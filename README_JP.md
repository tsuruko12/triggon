# triggon

[![PyPI](https://img.shields.io/pypi/v/triggon)](https://pypi.org/project/triggon/)
![Python](https://img.shields.io/pypi/pyversions/triggon)
![Python](https://img.shields.io/pypi/l/triggon)
![Package Size](https://img.shields.io/badge/size-36.2kB-lightgrey)
[![Downloads](https://pepy.tech/badge/triggon)](https://pepy.tech/project/triggon)

## 概要

Triggon は、繰り返しがちな条件分岐や一時的な状態変更の定型コードを減らすための Python ライブラリです。ラベルによる値の切り替え、遅延呼び出し、一時的な変更の復元、設定した戻り値を伴う早期終了をまとめて扱えます。分岐ロジックを 1 か所から書きやすく、再利用しやすく、制御しやすくすることが目的です。

## 目次

- [インストール](#%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB)
- [クイックスタート](#%E3%82%AF%E3%82%A4%E3%83%83%E3%82%AF%E3%82%B9%E3%82%BF%E3%83%BC%E3%83%88)
- [API リファレンス](#api-%E3%83%AA%E3%83%95%E3%82%A1%E3%83%AC%E3%83%B3%E3%82%B9)
  - [Triggon](#triggon)
  - [TrigFunc](#trigfunc)
  - [デバッグログ](#%E3%83%87%E3%83%90%E3%83%83%E3%82%B0%E3%83%AD%E3%82%B0)
  - [例外](#%E4%BE%8B%E5%A4%96)
- [ライセンス](#%E3%83%A9%E3%82%A4%E3%82%BB%E3%83%B3%E3%82%B9)
- [作者](#%E4%BD%9C%E8%80%85)

## 特徴

- `if` 文を書かずに、複数の値を一度に切り替え、登録した変数や属性もまとめて更新できます。
- `TrigFunc` によって遅延された関数やメソッドを実行できます。
- コンテキストマネージャ内で、設定した戻り値を指定して早期リターンできます。
- 条件や遅延を指定して、trigger / revert 操作をスケジュールできます。
- コンテキストマネージャを使って、一時的な変更を元に戻せます。

## インストール

```bash
pip install triggon
```

## クイックスタート

```python
from triggon import Triggon

tg = Triggon.from_labels(
    {
        "prod": "https://api.example.com",
        "dev": "http://localhost:8000",
    }
)


def get_base_url() -> str:
    return tg.switch_lit(("prod", "dev"), original_val="http://127.0.0.1:5000")


print(get_base_url())
# http://127.0.0.1:5000

tg.set_trigger("dev")
print(get_base_url())
# http://localhost:8000
```

## API リファレンス

### Triggon

推奨される生成方法は次の 2 つです。

```python
Triggon.from_label(label, /, new_values, *, debug=False) -> Triggon
Triggon.from_labels(label_values, /, *, debug=False) -> Triggon
```

`from_label()` は単一ラベルとその値を登録します。\
`from_labels()` はマッピングからラベルを登録でき、複数ラベルも一度に登録できます。

必要に応じて `Triggon(...)` で直接生成することもできます。

補足:

- ラベル値として渡した文字列以外のシーケンスは、そのラベルのインデックス付き値として展開されます
- 文字列以外のシーケンスを 1 つの値として扱いたい場合は、外側をさらにシーケンスで包んでください
- `set_trigger()`、`revert()`、`switch_lit()`、`register_ref()` などでは、ラベルの先頭に `*` を付けてインデックスを簡易的に指定できます。たとえば `*A` はラベル `A` の index `1`、`**A` は index `2` を意味します
- `debug` には `False`、`True`、単一のラベル名、またはログ出力対象のラベル名シーケンスを渡せます

```python
from triggon import Triggon

tg = Triggon.from_label("A", new_values=[1, 2, 3]) # 1つのラベルに複数のインデックス値を登録

tg = Triggon.from_labels(
    {
        "A": 10,
        "B": 20,
    }
)
```

#### `add_label()` / `add_labels()`

`add_label()` は、1つのラベルとその値を追加します

`add_labels()` は、マッピングを使って1つ以上のラベルとその値を追加します。

```python
add_label(label, new_values=None) -> None
add_labels(label_values) -> None
```

すでに登録済みのラベルは無視されます。

#### `set_trigger()`

1 つ以上のラベルを有効化します。ラベルに紐付いた登録対象があれば、その値も同時に更新されます。

```python
set_trigger(
    labels=None,
    /,
    *,
    indices=None,
    all=False,
    cond="",
    after=0,
    reschedule=False,
) -> None
```

`labels` には、単一のラベルまたはラベルのシーケンスを渡せます。

`indices` には、単一のインデックスまたはインデックスのシーケンスを渡せます。

適用される値が遅延済みの `TrigFunc` であれば、自動実行された結果が更新値として使われます。

`*` が付いたラベルでは、先頭の `*` の数がインデックスとして扱われます。\
ただし、明示的に指定した `indices` がある場合は、そちらが優先されます。

キーワード引数:

- `indices`: 各ラベルで使う値を明示的に指定するインデックス
- `all`: 登録済みの全ラベルを有効化します
- `cond`: 条件が `True` の場合のみラベルの有効化を適用します
- `after`: 指定秒数後にラベルを有効化します
- `reschedule`: 同じラベル群に対する既存の遅延予約を置き換えます

```python
from triggon import Triggon

tg = Triggon.from_labels({"A": 10, "B": 20})

tg.set_trigger(all=True)

print(tg.switch_lit("A", original_val=1))
# 10
print(tg.switch_lit("B", original_val=2))
# 20
```

```python
from time import sleep

x = 0

tg = Triggon.from_label("A", new_values=50)
tg.register_ref("A", name="x")

tg.set_trigger("A", after=0.5)

print(x)
# 0
sleep(0.6)
print(x)
# 50
```

#### `is_triggered()`

1 つ以上のラベルが現在有効かどうかを確認します。

```python
is_triggered(*labels, match_all=True) -> bool
```

`labels` には、複数の位置引数としてラベルを渡すことも、単一のラベルシーケンスを渡すこともできます。

`match_all` が `True` の場合は、指定したラベルがすべて有効なときにのみ `True` を返します。`False` の場合は、いずれか1つでも有効なら `True` を返します。

```python
tg = Triggon.from_labels({"A": 1, "B": 2})
tg.set_trigger("B")

print(tg.is_triggered("A"))
# False
print(tg.is_triggered("A", "B", match_all=False))
# True
```

#### `switch_lit()`

選択されたラベルに登録されている値を返します。指定されたラベルのいずれも有効でない場合は、`original_val` を返します。

```python
switch_lit(labels, /, original_val, *, indices=None) -> Any
```

`labels` には、単一のラベルまたはラベルのシーケンスを渡せます。

`indices` には、単一のインデックスまたはインデックスのシーケンスを渡せます。

複数ラベルが有効な場合は、シーケンス内で最初に有効なラベルが使われます。\
そのラベルで選択された値が `TrigFunc` によって遅延されている場合は、自動的に実行され、その結果が返されます。

`indices` を使うと、各ラベルでどの値を使うかを明示的に指定できます。\
`*` が付いたラベルでは、`*` の数によってインデックスが決まりますが、明示的に指定した `indices` がある場合はそちらが優先されます。

```python
tg = Triggon.from_labels({"A": "dev", "B": "prod"})

tg.set_trigger(all=True)

print(tg.switch_lit(("B", "A"), original_val="local"))
# prod
print(tg.switch_lit(("A", "B"), original_val="local"))
# dev
```

#### `register_ref()` / `register_refs()`

グローバル変数や属性パスを登録し、対応するラベルが有効になったときに `set_trigger()` で自動更新できるようにします。

```python
register_ref(label, /, name, *, index=None) -> None
register_refs(label_to_refs, /) -> None
```

補足:

- 通常のローカル変数は直接登録できません
- 属性パスの起点は現在のローカルスコープまたはグローバル名前空間から解決されます
- ラベルがすでに有効の場合、登録時に即座に対象を更新します
- 適用される値が遅延済みの `TrigFunc` であれば、更新時に自動実行されます
- 一致判定は現在のファイルと呼び出し箇所のスコープに基づいて行われます

`register_ref()` では、対象を登録した時点でそのラベルがすでに有効な場合、`index` を使って適用するインデックス値を指定できます。\
ラベルの先頭に `*` が付いている場合は、その `*` の数によってインデックスが決まりますが、明示的に指定した `index` がある場合はそちらが優先されます。

```python
from triggon import Triggon

tg = Triggon.from_labels({"enabled": True, "name": "prod"})

flag = False


class Config:
    value = "local"


tg.set_trigger("enabled")
tg.register_ref("enabled", name="flag") # "enabled" はすでに有効なので即時更新される
tg.register_ref("name", name="Config.value")

print(flag)
# True

tg.set_trigger("name")
print(Config.value)
# prod
```

`register_refs()` を使うと、`{label: {target_name: index}}` の形式で複数の対象をまとめて登録できます。

```python
tg.register_refs(
    {
        "enabled": {"flag": 0},
        "name": {"Config.value": 0},
    }
)
```

#### `is_registered()`

対象名が現在のファイルと呼び出し箇所のスコープ内で登録済みかどうかを確認します。

```python
is_registered(*names, label=None, match_all=True) -> bool
```

`names` には、複数の位置引数として対象名を渡すことも、単一の対象名のシーケンスを渡すこともできます。

判定は現在の値やオブジェクト状態ではなく、登録された名前情報に基づいて行われます。

キーワード引数:

- `label`: 判定対象を 1 つのラベルに絞り込みます
- `match_all`: 指定した全 name が登録済みのときだけ `True` を返します。いずれか 1 つでよい場合は `False` を使います。

```python
tg = Triggon.from_label("A", None)

a = 0
b = 0
tg.register_ref("A", name="a")

print(tg.is_registered("a", "b"))
# False
print(tg.is_registered("a", "b", match_all=False))
# True
```

#### `unregister_refs()`

選択したラベルから 1 つ以上の登録済み name を解除します。

```python
unregister_refs(names, /, *, labels=None) -> None
```

`names` は、1つの登録済み名前、またはそれらのシーケンスを受け取ります。

`labels` は、1つのラベル、またはラベルのシーケンスを受け取ります。

`labels` が指定された場合、そのラベルからのみ name を解除します。省略した場合は登録済みの全ラベルから解除されます。

#### `revert()`

ラベルを無効化し、登録済みの対象を元の値に戻します。

```python
revert(
    labels=None,
    /,
    *,
    all=False,
    disable=False,
    cond="",
    after=0,
    reschedule=False,
) -> None
```

`labels` は、1つのラベル、またはラベルのシーケンスを受け取ります。

キーワード引数:

- `all`: 登録済みの全ラベルを無効化します
- `disable`: 対象ラベルを永久的に無効化します
- `cond`: 条件が `True` の場合のみラベルの無効化を適用します
- `after`: 指定秒数後にラベルを無効化します
- `reschedule`: 同じラベル群に対する既存の遅延予約を置き換えます

```python
from triggon import Triggon

tg = Triggon.from_label("status", new_values="active")

tg.set_trigger("status")
print(tg.switch_lit("status", original_val="inactive"))
# active

tg.revert("status")
print(tg.switch_lit("status", original_val="inactive"))
# inactive
```

```python
tg = Triggon.from_label("status", new_values="active")


def get_status():
    tg.set_trigger("status")
    return tg.switch_lit("status", "inactive")


print(get_status())
# "active"

tg.revert("status", disable=True)
print(get_status())
# inactive
```

#### `capture_return()` / `trigger_return()`

指定したラベルが有効な場合に、スコープ付きのコンテキスト内で早期リターンします。

```python
capture_return() -> ContextManager[EarlyReturnResult]
trigger_return(labels, /, *, value=None) -> Any
```

`labels` は、1つのラベル、またはラベルのシーケンスを受け取ります。

`capture_return()` はコンテキストマネージャとして使い、その中で早期リターンしたい場合に `trigger_return()` を呼びます。

`EarlyReturnResult` で利用できるフィールド:

- `triggered`: `trigger_return()` が発動したかどうか
- `value`: 早期リターン時の戻り値

`trigger_return()` では、`value` を使って戻り値を指定できます。

補足:

- `trigger_return()` は `capture_return()` の中でのみ動作します
- `value` に渡した `TrigFunc` による遅延値は、結果が保存される前に `capture_return()` によって実行されます

```python
from triggon import Triggon

tg = Triggon.from_label("stop", new_values=True)


def task():
    print("start")
    tg.trigger_return("stop", value="stopped")
    print("end")


def main():
    with tg.capture_return() as result:
        task()
        print("after task")
    return result


result = main()
# start
# end
# after task
print(result.triggered)
# False
print(result.value)
# None

tg.set_trigger("stop")

result = main()
# start
print(result.triggered)
# True
print(result.value)
# stopped
```

#### `trigger_call()`

指定したラベルのいずれかが有効な場合に、遅延された `TrigFunc` の対象を実行します。

```python
trigger_call(labels, /, target) -> Any
```

`labels` は、1つのラベル、またはラベルのシーケンスを受け取ります。

`target` には、呼び出しで終わる遅延 `TrigFunc` の呼び出しチェーンを指定する必要があります。

```python
from triggon import TrigFunc, Triggon

tg = Triggon.from_label("debug", new_values=True)
f = TrigFunc()


def show_debug():
    print("debug mode")


tg.trigger_call("debug", target=f.show_debug())
# 出力なし

tg.set_trigger("debug")
tg.trigger_call("debug", target=f.show_debug())
# debug mode
```

#### `rollback()`

対象の値を一時的に変更し、コンテキストを抜けると自動的に元に戻します。

```python
rollback(targets=None) -> ContextManager[None]
```

補足:

- CPython 3.13 以降が必要です
- `"x"` や `"obj.value"` のような対象名を明示的に渡せます
- `targets` を省略した場合は、ブロック内の代入対象が自動的に収集されます

```python
from triggon import Triggon

x = 1

with Triggon.rollback():
    x = 99
    print(x)
    # 99

print(x)
# 1
```

### TrigFunc

`TrigFunc` は、関数やメソッドの呼び出しをすぐに実行せず、遅延呼び出しとして記録します。\
記録されたチェーンは、あとから `switch_lit()`、`trigger_call()`、`trigger_return()` で利用できます。

```python
TrigFunc()
```

主な用途:

- `switch_lit()` 用のラベルデータに遅延値を保存する
- `trigger_call()` で遅延呼び出しを実行する
- `trigger_return()` で遅延値を戻り値として返す

遅延された名前は、チェーン実行時に、捕捉されたローカルスコープ・グローバルスコープ・builtins から解決されます。\
`TrigFunc` のインスタンス自体も、スコープをまたいで再利用できます。

```python
from triggon import TrigFunc, Triggon

def greet(name):
    return f"hello, {name}"


f = TrigFunc()
tg = Triggon.from_label("greet", new_values=f.greet("world"))

tg.set_trigger("greet")
print(tg.switch_lit("greet", original_val=None))
# hello, world
```

### デバッグログ

`Triggon(...)`、`from_label()`、`from_labels()` に `debug=` を渡すことで、デバッグ出力を有効にできます。

- `debug=False`: ログ出力を無効にします
- `debug=True`: 環境変数の設定を使います。未設定の場合は verbosity `3` が使われます
- `debug="A"` または `debug=("A", "B")`: 出力対象を指定したラベルに限定します

環境変数:

- `TRIGGON_LOG_VERBOSITY`
  - `0`: オフ
  - `1`: trigger、revert、early-return、trigger-call のイベントを記録
  - `2`: さらに値の更新も記録
  - `3`: さらに遅延処理や register / unregister イベントも記録
- `TRIGGON_LOG_FILE`: stderr の代わりにファイルへログを書き込みます
- `TRIGGON_LOG_LABELS`: `debug=True` のときに使われる、カンマ区切りのラベルフィルタ

### 例外

- `InvalidArgumentError`: 公開 API に無効な引数、または無効な引数の組み合わせが渡された場合
- `UnregisteredLabelError`: 登録されていないラベルを操作しようとした場合
- `InactiveCaptureError`: `capture_return()` の外で `trigger_return()` が呼ばれた場合
- `RollbackNotSupportedError`: `rollback()` が CPython 3.13 より前の実行環境で使われた場合
- `UpdateError`: 登録された対象を更新または復元できなかった場合

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。
詳細は [LICENSE](./LICENSE) を参照してください。

## 作者

作者: Tsuruko
GitHub: [@tsuruko12](https://github.com/tsuruko12)
X: [@tool_tsuruko12](https://x.com/12tsuruko)
