# ai-project-loop 実行指示

`~/.claude/skills/ai-project-loop/SKILL.md`(ai-project-loop スキル)を呼び出し、
その手順どおりに1サイクル実行する。

- 作業リポジトリ: `C:\dev\ai-project-loop`
- 情報源: `C:\Users\PC_User\ObsidianVault\10_情報/AI Archive\`(読み取り専用)
- セッション内ループとして呼ばれた場合のみ、サイクル完了後に ScheduleWakeup(300秒)で次サイクルを予約する
- 定期実行(headless)から呼ばれた場合は1サイクルで終了する
