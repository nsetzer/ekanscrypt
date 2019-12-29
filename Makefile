
.PHONY: cover
cover:
	coverage run -m tests
	coverage html --omit "venv/*,*_test.py,tests/*"
	#open htmlcov/index.html

.PHONY: cover_lexer
cover_lexer:
	coverage run -m tests.lexer_test
	coverage html --omit "venv/*,*_test.py,tests/*"
	#open htmlcov/index.html


.PHONY: cover_parser
cover_parser:
	coverage run -m tests.parser_test
	coverage html --omit "venv/*,*_test.py,tests/*"
	#open htmlcov/index.html

.PHONY: cover_compiler
cover_compiler:
	coverage run -m tests.compiler_test
	coverage html --omit "venv/*,*_test.py,tests/*"
	#open htmlcov/index.html

.PHONY: cover_program
cover_program:
	coverage run -m tests.program_test
	coverage html --omit "venv/*,*_test.py,tests/*"
	#open htmlcov/index.html