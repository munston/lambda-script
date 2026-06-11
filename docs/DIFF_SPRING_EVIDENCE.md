# Diff spring evidence

```text
$ python -S scripts/diff_spring/absorb_json.py --self-test
OK diff spring parser self-test
$ python -S scripts/diff_spring/absorb_json.py --list
docs/example.txt
README.md
$ python -S scripts/diff_spring/absorb_json.py --message-only
Absorb json test
$ python -S scripts/diff_spring/absorb_json.py
OK absorbed 2 file operation(s)
ARCHIVED: /mnt/data/diff_spring_test_repo/spring/diff/archive/20260611T115642Z-incoming.json
COMMIT_MESSAGE: Absorb json test
```
