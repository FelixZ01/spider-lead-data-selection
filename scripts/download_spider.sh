#!/usr/bin/env bash
set -euo pipefail

base_url="https://raw.githubusercontent.com/taoyds/spider/master/evaluation_examples/examples"
target_dir="${1:-data/raw/spider}"
mkdir -p "$target_dir"

for filename in train_spider.json dev.json tables.json; do
  curl --fail --location --retry 3 "$base_url/$filename" --output "$target_dir/$filename"
done

echo "Downloaded official Spider 1.0 examples to $target_dir"
