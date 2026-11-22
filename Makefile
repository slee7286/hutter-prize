.DELETE_ON_ERROR:
.PHONY: baseline corpus
baseline: data/sample
	@mkdir -p build
	@gzip -n -6 -c $< > build/sample.gz
	@gzip -dc build/sample.gz | cmp $< -
	@wc -c $< build/sample.gz
	@printf 'Byte-for-byte round trip passed.\n'

corpus: data/enwik9

data/sample: data/enwik9
	@dd if=$< of=$@ bs=1048576 count=1 status=none

data/enwik9:
	@mkdir -p data
	@set -eu; tmp=$$(mktemp -d data/download.XXXXXX); trap 'rm -rf "$$tmp"' EXIT; \
	curl -fsSL --retry 2 https://mattmahoney.net/dc/enwik9.zip -o "$$tmp/data.zip"; \
	unzip -p "$$tmp/data.zip" enwik9 > "$$tmp/enwik9"; \
	test "$$(wc -c < "$$tmp/enwik9")" = 1000000000; \
	printf '%s  %s\n' e206c3450ac99950df65bf70ef61a12d "$$tmp/enwik9" | md5sum -c -; \
	mv "$$tmp/enwik9" $@
