rm lambda.zip -f
uv build
uv run pip install --upgrade -t build dist/*.whl
cd build || exit 1
zip -r ../lambda.zip . -x '*.pyc'
cd .. || exit 1
zip -u lambda.zip lambda_function.py config.toml auth.lambda.toml
