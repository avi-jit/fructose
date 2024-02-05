# Fructose: LLM calls as strongly-typed functions

Implement LLM calls as python functions, using the docstring and type signatures to establish the API.
```
from fructose import send

@send()
def get_theme(words: list[str]) -> str:
  """
  This function takes a list of words and returns a theme.
  """

theme = get_theme(["cat", "dog", "bird"])
print(theme) # animals
```
The @send() decorator introspects the function and builds a prompt to an LLM to perform the task whenever the function is invoked.

---

### Stability
We are in v0, meaning the API is unstable version-to-version. Pin your versions to ensure new builds don't break!
Also note... since LLM generations are nondeterminsitic, the calls may break too!

### To develop

From the root of this repo:

Create a virtual env
``` bash
python3 -m venv venv
. ./venv/bin/activate
```

Install fructose into your pip environment with:
``` bash
pip3 install -e .
```
This installs the fructose package in editable mode. All imports of fructose will run the fructose source at `./src/fructose` directly.

Run the demo with:
``` bash
python3 demo.py
```

Run tests with:
``` bash
python3 -m pytest
```
