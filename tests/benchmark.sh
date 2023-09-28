docker build --target execute --tag notifier:execute .

rm -f run.log
echo "Time,Log" > run.log

docker run --rm notifier:execute config/config.toml config/auth.local.toml --dry-run --execute-now hourly 2>&1 | stdbuf -oL sed 's/,[0-9]\+ - |:[0-9]\+ - /,/g' | tee --append run.log