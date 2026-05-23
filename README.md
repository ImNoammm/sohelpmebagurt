# SoHelpMeBagrut

**AI-powered Israeli Bagrut exam tutor** — [sohelpmebagurt](https://imnoammm.github.io/sohelpmebagurt/)

Each subject has a `skill.md` file that turns any AI assistant (Claude, ChatGPT, etc.) into a Bagrut tutor for that subject. Paste the link into your AI and it becomes a patient Hebrew-speaking teacher.

## How it works

- **Past exams** are fetched weekly from the [Ministry of Education archive](https://meyda.education.gov.il) via a GitHub Actions workflow and written into each `skill.md`.
- **Claude Desktop users** get an extra MCP (Model Context Protocol) server that lets Claude read PDF pages directly — so it can see figures, diagrams and tables from the real exam papers.
- **All other AIs** get a plain-text `skill.md` with question text and worked solutions.

## Subjects

| Subject | Status |
|---|---|
| Computer Science — C# | ✅ Available |
| Computer Science — Java | ✅ Available |
| Mathematics (5 units) | ✅ Available |
| Physics | 🔜 Coming soon |
| English | 🔜 Coming soon |

## Report a problem

Open an issue on [GitHub Issues](https://github.com/ImNoammm/sohelpmebagurt/issues) — broken exam links, wrong answers, missing subjects, anything.
