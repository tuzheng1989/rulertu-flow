#!/usr/bin/env node
/**
 * rulertu-flow 提交文案路由守卫(PreToolUse,提醒不拦截)。
 *
 * 识别 Bash/PowerShell 命令中的 `git commit` 与 `gh pr create/edit`,
 * 扫描当前会话 transcript:对应技能(commit/pr)未加载时向模型注入
 * 一次 additionalContext 提醒;已加载或本会话已提醒过则静默。
 * 任何异常都静默放行(fail-open),不阻断提交。
 */
'use strict';

const fs = require('fs');

const TARGETS = {
  commit: {
    // 提醒文案本身含技能名,写入 transcript 后即视为"已提醒过",天然每会话只提醒一次
    loadedRe: /rulertu-flow:commit|"skill"\s*:\s*"(?:rulertu-flow:)?commit"/,
    message:
      '[rulertu-flow] 本次 git commit 的 message 应先经 rulertu-flow:commit 技能依据实际 diff 起草(标题写具体变化,正文按需补原因与约束);会话中已起草或用户明确要求跳过时,直接继续。',
  },
  pr: {
    loadedRe: /rulertu-flow:pr|"skill"\s*:\s*"(?:rulertu-flow:)?pr"/,
    message:
      '[rulertu-flow] 创建或更新 PR 的标题与正文应先经 rulertu-flow:pr 技能依据最终 diff 起草;会话中已起草或用户明确要求跳过时,直接继续。',
  },
};

/** 按复合命令分隔符切分子命令;引号内分隔符不做完整解析,误报仅多一次提醒 */
function splitSegments(command) {
  return String(command)
    .split(/;|&&|\|\||\||\n/)
    .map((seg) => seg.trim())
    .filter(Boolean);
}

/** git 全局选项中需要独立跟一个值的;其余含 `=` 的选项值内联、flag 不带值 */
const GIT_VALUE_OPTS = new Set(['-C', '--git-dir', '--work-tree', '--namespace']);

/** 返回 git 命令的子命令名:第一个非选项 token(跳过带值选项的值),找到即停 */
function gitSubcommand(tokens) {
  let i = 1;
  while (i < tokens.length) {
    const tok = tokens[i];
    if (GIT_VALUE_OPTS.has(tok)) i += 2;
    else if (tok.startsWith('-')) i += 1; // 含 `=` 的内联值与 flag 都只占一个 token
    else return tok;
  }
  return null;
}

/**
 * 判断命令是否命中提交/PR 文案场景。
 * 只认段首可执行文件为 git/gh 时的目标子命令,避免 `echo git commit` 误报。
 */
function detectTarget(command) {
  for (const seg of splitSegments(command)) {
    const tokens = seg.split(/\s+/);
    const head = tokens[0];
    if (head === 'git' && gitSubcommand(tokens) === 'commit') return 'commit';
    if (head === 'gh' && tokens[1] === 'pr' && tokens.slice(2).some((t) => t === 'create' || t === 'edit')) {
      return 'pr';
    }
  }
  return null;
}

/** transcript 文本中是否已出现对应技能的调用或本守卫的提醒记录 */
function skillLoaded(transcriptText, target) {
  const conf = TARGETS[target];
  return Boolean(conf && transcriptText && conf.loadedRe.test(transcriptText));
}

/** 组装 PreToolUse 的 additionalContext 输出 */
function buildOutput(target) {
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      additionalContext: TARGETS[target].message,
    },
  });
}

function main(input) {
  if (input.tool_name !== 'Bash' && input.tool_name !== 'PowerShell') return null;
  const target = detectTarget((input.tool_input || {}).command || '');
  if (!target) return null;

  let transcriptText = '';
  if (input.transcript_path) {
    try {
      transcriptText = fs.readFileSync(input.transcript_path, 'utf8');
    } catch {
      transcriptText = ''; // transcript 不可读时按未加载处理,仅多提醒一次
    }
  }
  return skillLoaded(transcriptText, target) ? null : buildOutput(target);
}

if (require.main === module) {
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => (raw += chunk));
  process.stdin.on('end', () => {
    try {
      const out = main(JSON.parse(raw));
      if (out) process.stdout.write(out);
    } catch {
      // 输入异常时静默放行
    }
  });
}

module.exports = { splitSegments, detectTarget, skillLoaded, buildOutput, TARGETS };
