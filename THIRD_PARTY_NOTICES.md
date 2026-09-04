# Third-Party Notices

Our own code in this repo is MIT-licensed — see `LICENSE`.

## dsh — DeepSeek Harness (MIT)

- **What it is:** the upstream open-source agent harness
  (https://github.com/deepseek-ai/deepseek-harness) this workbench builds
  on. We did not write dsh; we build our authorization layer and tools on
  top of it, using it as the plugin runtime / plugin host.
- **License:** MIT. dsh's actual license text is reproduced below.
- **Pinned version:** `@deepseek-ai/dsh` at exactly `0.1.2-rc.1`
  (`package.json`, no `^`/`~` range). The pin is exact because dsh is a
  developer preview whose own README warns to expect
  compatibility-breaking changes between releases — a floating range could
  silently pull a breaking harness under this workbench, so upgrades are a
  deliberate, reviewed commit, never an accident of `npm install`.
- **Vendoring note:** we do not vendor dsh's source directly, so we do not
  duplicate its own third-party notices here — for the full transitive
  dependency disclosures, see dsh's own `THIRD_PARTY_NOTICES.md` upstream
  at https://github.com/deepseek-ai/deepseek-harness/blob/master/THIRD_PARTY_NOTICES.md.

```text
MIT License

Copyright (c) 2026 DeepSeek

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
