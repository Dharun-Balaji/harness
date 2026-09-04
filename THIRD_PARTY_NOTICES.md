# Third-Party Notices

This repo's own code is MIT-licensed (see `LICENSE`).

## dsh — DeepSeek Harness (MIT License)

- **Role in this project:** Node/TypeScript plugin runtime, invoked by the
  Python orchestrator as an out-of-process subprocess / plugin host. dsh
  is not ported to Python and is not vendored in this repo as of Phase 0.
- **License:** MIT. The MIT license requires the copyright + permission
  notice to travel with the code, which is why it is reproduced here and
  must be kept when dsh is added as a dependency, submodule, or vendored
  directory in later phases.

```text
MIT License

Copyright (c) DeepSeek Harness contributors

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

**Integration note (binding for later phases):** do not copy dsh source
into this repo without keeping this notice adjacent to it, and record the
exact dsh version/commit in the README and in any lockfile or submodule
pointer so runs stay reproducible.
