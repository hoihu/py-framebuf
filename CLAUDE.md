# Micropython Framebuf as pure python

The goal is to create a pure-python implementation of Micropython Framebuf
module, which is written in C-code.

We want it to be competitive in speed, so use either `viper` syntax of `asm_thumb`
optimisations.

It shall support all color modes.

Test it by uploading test files to the attached micropython board, which
is accessible via RFC2217 (see also your skills)

Test it against the C-code implementations and make it a 1:1 fit, so there
is no difference between c-code and pure-python code.

It would be nice to have the implementation of pixel, hline, vline, fill.
Bonus points if you compare speed of executions (with different framebuf sizes etc)
but focus first on correct implementations across different framebuf sizes and color modes!

I've supplied you the micropython source code, where also the online documentation
of viper etc optimisations is available (also framebuf color modes etc.)

before accessing the micropython board initially (for the first time), make sure to
erase all files on the board using `python -m there -p .... rm -r /`

Use the python venv below `./venvdev`!
