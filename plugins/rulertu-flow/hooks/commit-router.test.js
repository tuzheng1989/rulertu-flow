'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { detectTarget, skillLoaded, buildOutput, TARGETS } = require('./commit-router.js');

test('detectTarget 识别各类 git commit 形态', () => {
  const cases = [
    'git commit -m "feat: x"',
    'git commit',
    'git -C /a/b commit -m x',
    'git --no-pager commit --amend',
    'git commit -F - <<EOF\nfeat: y\nEOF',
    'cd /repo && git add . && git commit -m "z"',
    'git status; git commit -m w',
    'git log || git commit',
  ];
  for (const cmd of cases) assert.equal(detectTarget(cmd), 'commit', `应识别: ${cmd}`);
});

test('detectTarget 不误报非提交命令', () => {
  const cases = [
    '',
    'ls -la',
    'git log --oneline',
    'git status --short',
    'git add .',
    'git checkout -b feat/x',
    'git log --grep commit -3',
    'echo git commit',
    'echo "git" && echo "commit"',
    'git revert HEAD',
    'git cherry-pick abc123',
    'git show HEAD:commit-msg.txt',
  ];
  for (const cmd of cases) assert.equal(detectTarget(cmd), null, `不应识别: ${cmd}`);
});

test('detectTarget 识别 gh pr create/edit,不误报其他 gh 子命令', () => {
  assert.equal(detectTarget('gh pr create --title x'), 'pr');
  assert.equal(detectTarget('gh pr edit 5 --body y'), 'pr');
  assert.equal(detectTarget('gh pr create --web'), 'pr');
  assert.equal(detectTarget('gh pr view 5'), null);
  assert.equal(detectTarget('gh pr merge 5'), null);
  assert.equal(detectTarget('gh repo create x'), null);
});

test('skillLoaded 按技能名或 Skill 调用记录判定', () => {
  const skillCall = '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"rulertu-flow:commit"}}]}}';
  assert.equal(skillLoaded(skillCall, 'commit'), true);
  assert.equal(skillLoaded('{"skill":"commit","args":""}', 'commit'), true);
  // 守卫自身的提醒文案写入 transcript 后,同样视为已处理(每会话最多提醒一次)
  assert.equal(skillLoaded(TARGETS.commit.message, 'commit'), true);
  // 目标不匹配时不算加载
  assert.equal(skillLoaded(skillCall, 'pr'), false);
  assert.equal(skillLoaded('', 'commit'), false);
  assert.equal(skillLoaded(undefined, 'commit'), false);
});

test('buildOutput 输出合法的 PreToolUse additionalContext', () => {
  for (const target of ['commit', 'pr']) {
    const parsed = JSON.parse(buildOutput(target));
    assert.equal(parsed.hookSpecificOutput.hookEventName, 'PreToolUse');
    assert.ok(parsed.hookSpecificOutput.additionalContext.includes(`rulertu-flow:${target}`));
  }
});
