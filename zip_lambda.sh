# https://chariotsolutions.com/blog/post/building-lambdas-with-poetry/
poetry build
poetry run pip install --upgrade -t build dist/*.whl
cd build || exit
zip -r ../lambda.zip . -x '*.pyc'
