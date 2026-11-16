import importlib.util
import json
import shutil
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load_collect():
    spec = importlib.util.spec_from_file_location("collect", SCRIPTS / "collect.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ZCodeCollectTests(unittest.TestCase):
    def setUp(self):
        self.collect = _load_collect()
        self.root = Path(__file__).resolve().parent / ("scratch_" + uuid.uuid4().hex)
        self.rollout = self.root / "rollout"
        self.rollout.mkdir(parents=True)
        self._orig = self.collect.ZCODE_ROLLOUT
        self.collect.ZCODE_ROLLOUT = self.rollout

    def tearDown(self):
        self.collect.ZCODE_ROLLOUT = self._orig
        shutil.rmtree(self.root)

    def write_session(self, sid, records):
        (self.rollout / f"model-io-{sid}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
            encoding="utf-8")

    def rec(self, minutes_ago, messages, query_source="main_turn", resp_text=""):
        started = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        rec = {
            "querySource": query_source,
            "startedAt": started.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "request": {"messages": messages},
        }
        resp = {"usage": {"inputTokens": 100, "outputTokens": 50}}
        if resp_text:
            resp["text"] = resp_text
        rec["response"] = resp
        return rec

    def user_msg(self, text):
        return {"role": "user", "content": text}

    def test_window_filter_and_message_filters(self):
        inside = "把 collect.py 的 ZCode 会话采集改成解析完整内容"
        env_sys = ("# Environment\nYou have been invoked in the following environment: \n"
                   " - Primary working directory: D:\\runspace\\rulertu-flow\n")
        self.write_session("sess_aaa11111", [
            self.rec(30, [{"role": "system", "content": env_sys},
                          self.user_msg("<system-reminder>\nCodebase instructions\n</system-reminder>"),
                          self.user_msg(inside)]),
            self.rec(20, [{"role": "tool", "content": "工具结果"}],
                     resp_text="已完成改造。"),
            self.rec(10, [self.user_msg("继续")]),                      # trivial 输入
            self.rec(5, [self.user_msg(inside)]),                       # attempt 重试重复
            self.rec(3, [], query_source="session_title", resp_text="标题"),  # 非主轮次
            self.rec(2 * 24 * 60, [self.user_msg("窗口外的旧输入")]),     # 窗口外
        ])
        start, end = self.collect.days_range(1)
        result = self.collect.collect_zcode(start, end)
        self.assertEqual(list(result.keys()), ["rulertu-flow"])
        items = result["rulertu-flow"]["items"]
        self.assertEqual([i["content"] for i in items], [inside])
        self.assertLessEqual(len(items[0]["content"]), 300)
        self.assertNotIn("session_summaries", result["rulertu-flow"])

    def test_summarize_attaches_recap_outcome_and_tokens(self):
        outcome = "ZCode 会话内容解析已全部完成，新旧测试全过，深度摘要与 token 统计一并接入。"
        self.write_session("sess_bbb22222", [
            self.rec(30, [self.user_msg("调研 rollout 文件格式")],
                     resp_text="我先读一遍 rollout 的诊断文件格式。"),
            self.rec(10, [{"role": "tool", "content": "结果"}], resp_text=outcome),
        ])
        start, end = self.collect.days_range(1)
        result = self.collect.collect_zcode(start, end, summarize=True)
        group = result["zcode"]  # 无 cwd 注入，归入 zcode 组
        self.assertEqual(len(group["items"]), 1)
        summary = group["session_summaries"]["bbb22222"]
        self.assertIn("rollout", summary["recap"])
        self.assertIn("全部完成", summary["outcome"])
        self.assertTrue(summary["milestones"])
        self.assertEqual(summary["total_tokens"], 300)
        self.assertEqual(summary["turns"], 2)

    def test_list_content_and_unknown_project_fallback(self):
        self.write_session("sess_ccc33333", [
            self.rec(15, [{"role": "user", "content": [
                {"type": "text", "text": "检查 usage 字段的累计逻辑是否正确"}]}]),
        ])
        start, end = self.collect.days_range(1)
        result = self.collect.collect_zcode(start, end)
        self.assertEqual(result["zcode"]["items"][0]["content"],
                         "检查 usage 字段的累计逻辑是否正确")

    def test_missing_dir_returns_empty(self):
        self.collect.ZCODE_ROLLOUT = self.root / "missing"
        start, end = self.collect.days_range(1)
        self.assertEqual(self.collect.collect_zcode(start, end), {})


if __name__ == "__main__":
    unittest.main()
