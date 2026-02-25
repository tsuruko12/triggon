# triggon
[![PyPI](https://img.shields.io/pypi/v/triggon)](https://pypi.org/project/triggon/)
![Python](https://img.shields.io/pypi/pyversions/triggon)
![Python](https://img.shields.io/pypi/l/triggon)
![Package Size](https://img.shields.io/badge/size-31kB-lightgrey)
[![Downloads](https://pepy.tech/badge/triggon)](https://pepy.tech/project/triggon)

> **警告**
> 次回のアップデートでは破壊的変更（API変更）を含む予定です。  
> `switch_var` API関数の名称変更に加え、一部の引数名も変更されます。

# 概要
このライブラリはラベル付きトリガーポイントで値や関数を動的に切り替えることができます。 

## 目次
- [インストール方法](#インストール方法)
- [使い方](#使い方)
- [ライセンス](#ライセンス)
- [開発者](#開発者)

## 特徴
- １つのトリガーポイントで複数の値や関数を一度に切り替え
- `if` や `match` 文を書く必要なし 
- リテラル値・変数の両方の切り替え可能
- 任意の戻り値で早期リターンが可能
- 関数を好きなタイミングで呼び出し可能  
- ほとんどのライブラリ関数やカスタム関数を遅延実行できる  

## 追加予定機能
- 環境変数で設定できるデバッグ設定を追加（verbosity、ファイル出力、対象ラベル）
- ラベルと値の登録処理を、単一ラベル用・複数ラベル用の2つのクラスメソッドに分割
- 遅延実行クラスで、関数やクラスメソッドをより柔軟な方法で渡せるように対応

## インストール方法
```bash
pip install triggon
```

## 使い方
このセクションでは、API の使い方を説明します。

## API Reference
- [Triggon](#triggon)
  - [set_trigger](#set_trigger)
  - [is_triggered](#is_triggered)
  - [switch_lit](#switch_lit)
  - [switch_var](#switch_var)
  - [is_registered](#is_registered)
  - [revert](#revert)
  - [exit_point](#exit_point)
  - [trigger_return](#trigger_return)
  - [trigger_func](#trigger_func)
- [TrigFunc](#trigfunc)
- [Erorr](#error)
  - [InvalidArgumentError](#invalidargumenterror)
  - [InvalidClassVarError](#invalidclassvarerror)
  - [MissingLabelError](#missinglabelerror)

### Triggon
`self, label: str | dict[str, Any], /, new: Any = None,`  
`*, debug: bool | str | list[str] | tuple[str, ...] = False`

`Triggon()` はラベルと値のペアで初期化されます。  
単一のラベルとその値、または辞書で複数のラベルを渡すことが可能です。

配列を使って1つのラベルに複数の値を渡した場合、  
それぞれの値は、指定した順にインデックス 0、1、2... に対応します。

```python
from triggon import Triggon

# インデックス1に100、インデックス2に0を変更値として設定
tg = Triggon("num", new=[100, 0])

def example():
    x = tg.switch_lit("num", 0)    # インデック 0
    y = tg.switch_lit("*num", 100) # インデック 1

    print(f"{x} -> {y}")

example()
# 出力: 0 -> 100

tg.set_trigger("num")

example()
# 出力: 100 -> 0
```

１つの値としてリストやタプルを渡したい場合は、  
１つの値として認識できるように、さらに別のリストやタプルで包んでください。

```python
tg = Triggon({
    "seq1": [(1, 2, 3)], # インデックス0に (1, 2, 3)
    "seq2": [1, 2, 3],   # インデックス0, 1, 2に1, 2, 3を設定
})

def example():
    x = tg.switch_lit("seq1", 10) # インデック 0
    y = tg.switch_lit("seq2", 10) # インデック 0

    print(f"seq1 の値: {x}")
    print(f"seq1 の値: {y}")

tg.set_trigger(("seq1", "seq2"))

example()
# == 出力 ==
# seq1 の値: (1, 2, 3)
# seq2 の値: 1
```

１つのインデックスに対して、複数の値を割り当てることも可能です。

```python
from dataclasses import dataclass

from triggon import Triggon

tg = Triggon("mode", new=True) # "mode"ラベルのインデックス0にTrueを設定

@dataclass
class ModeFlags:
    mode_a: bool = False
    mode_b: bool = False
    mode_c: bool = False

    def set_mode(self, enable: bool):
        tg.set_trigger("mode", cond="enable")

        tg.switch_var("mode", [self.mode_a, self.mode_b, self.mode_c]) # すべて同じインデックス0を共有

        print(
            f"mode_a is {self.mode_a}\n"
            f"mode_b is {self.mode_b}\n"
            f"mode_c is {self.mode_c}\n"
        )

s = ModeFlags()

s.set_mode(Fa式se)
# == 出力 ==
# mode_a is False
# mode_b is False
# mode_c is False

s.set_mode(True)
# == 出力 ==
# mode_a is True
# mode_b is True
# mode_c is True
```

ラベルの状態をリアルタイムで追跡したい場合は、`debug` フラグを `True` を指定してください。　 
デバッグ出力したいラベルを単体、またはそれを含めたタプル/リストで渡すことで、  
出力をソートすることができます。

```python
Triggon({"A": 10, "B": 20}, debug=True)       # "A"と"B"両方出力

Triggon({"A": 10, "B": 20}, debug="A")        # "A"のみ出力

Triggon({"A": 10, "B": 20}, debug=("A", "B")) # 出力なし
```

> ⚠️ **Note:** 
> `*` プレフィックス付きのラベルは初期化時には使用できず、`InvalidArgumentError` が発生します。　

---

### set_trigger
`self, label: str | list[str] | tuple[str, ...], /,`  
`*,`  
`all: bool = False,`  
`index: int = None,`  
`cond: str = None,`  
`after: int | float = None`  
`-> None`

指定されたラベルを有効化します。
`switch_var()` によって変数が登録済みの場合は、この関数内で変数値を切り替えます。

`revert()` で `disable=True` に設定されてる場合、そのラベルは有効化されません。

#### ***all***
`True` に設定すると、すべてのラベルを有効にします。

#### ***index***
値を切り替える際のラベルのインデックス値を指定します。  
指定されてない場合は、`switch_var()` で指定されたインデックスが使用されます。  

これは `switch_var()` にのみ適用され、`switch_lit()` には適用されません。

#### ***cond***
ラベルを有効にする条件を設定します。

> **⚠️ Note:**  
> この引数の処理には内部的に `eval()` を使用します。  
> **比較式のみ許可**されています（例: `x > 0 > y`, `value == 10`）。  
> 単体のリテラル値、または変数が渡された場合、  
> 値が `ブール値` 以外の時 `InvalidArgumentError` が発生します。  
> 関数呼び出しの場合も同様です。

#### ***after***
ラベルを有効化するまでの遅延時間を秒数で指定します。  
遅延中に再度指定された場合は上書きされずに、最初の秒数が維持されます。

> **⚠️ Note:**  
> 実際の実行は、指定した時間より **およそ 0.011 秒後** に行われます。

```python
import random

from triggon import Triggon

tg = Triggon({
    "timeout": None, 
    "mark": ("〇", "✖"), 
    "add": (1, 0),
})

mark = None
point = None
correct = 0
tg.switch_var({"mark": mark, "add": point}) # 変数を登録

print("10秒間で何問正解できる？")
tg.set_trigger("timeout", after=10) # 10秒後にラベル"timeout"を有効にする

for _ in range(15):
    x = random.randint(1, 10)
    y = random.randint(1, 10)

    answer = int(input(f"{x} × {y} = ") or 0)
    tg.set_trigger(("mark", "add"), cond="answer == x*y")          # "mark" -> "〇", "add" -> 1
    tg.set_trigger(("mark", "add"), index=1, cond="answer != x*y") # "mark" -> "✖", "add" -> 0
    print(mark)

    correct += point

    if tg.is_triggered("timeout"): # ラベル"timeout"が有効にされてるか確認
        print("タイムアップ！")
        print(f"{correct}問正解！")
        break
```

```python
tg = Triggon("msg", new="呼びましたか？")

def sample(print_msg: bool):
    # print_msgがTrueの場合に"msg"のフラグを有効にする
    tg.set_trigger("msg", cond="print_msg")

    # "msg"フラグが有効な場合、テキストを出力する
    print(tg.switch_lit("msg", ""))

sample(False) # Output: ""
sample(True)  # Output: 呼びましたか？ 
```

---

### is_triggered
`self, label: str | list[str] | tuple[str, ...]`  
`-> bool | list[bool] | tuple[bool, ...]`

指定されたラベルごとに、有効かどうかを `True` または `False` で返します。  
返り値の型は渡された引数によって変わります。

```python
from triggon import Triggon

tg = Triggon({"A": None, "B": None, "C": None, "D": None})

tg.set_trigger(("A", "D"))

print(tg.is_triggered("A"))                # 出力: True
print(tg.is_triggered(["C", "D"]))         # 出力: [False, True]
print(tg.is_triggered("A", "B", "C", "D")) # 出力: (True, False, False, True)
```

---

### switch_lit
`self, label: str | list[str] | tuple[str, ...], /,`  
`org: Any,`  
`*, index: int = None`  
`-> Any`

ラベルが有効な場合に、その値を切り替えます。  
複数のラベルが渡されていて、そのうち複数が有効な場合は、  
配列内でインデックスが小さいものが優先されます。

**変数を直接参照することはできません。**

戻り値が `TrigFunc` クラスで遅延実行されてる関数の場合、  
それを自動的に実行しその戻り値を返します。

複数のラベルに対して `index` キーワードが指定された場合は、  
全てのラベルに適用されます。

```python
from triggon import Triggon, TrigFunc

F = TrigFunc() # 関数の遅延実行用ラッパ
tg = Triggon("text", new=F.print("After")) 

def example():
    tg.switch_lit("text", org=F.print("Before"))

example() # 出力: Before

tg.set_trigger("text")
example() # 出力: After
```

また、インデックスを指定するために、接頭辞として `*` を使うこともできます。  
たとえば、`"label"` はインデックス 0 を、`"*label"` はインデックス１を指します。
接頭辞以外の場所で使われた `*` はインデックスとして認識されないので、無視されます。
キーワード引数と `*` 両方が指定されている場合は、**キーワード引数の方が優先されます。**  

> **Note:**  複数のインデックスを扱う場合は、可読性のため`index`キーワードの使用を推奨します。

```python
# インデックス 0 に "A" を、インデックス 1 に "B" を設定
tg = Triggon("char", new=("A", "B"))

def example():
    tg.set_trigger("char")

    print(tg.switch_lit("char", 0))           # インデックス 0（'*'なし＝デフォルトでインデックス0）
    print(tg.switch_lit("*char", 1))          # インデックス 1（'*'で指定）
    print(tg.switch_lit("*char", 0, index=0)) # インデックス 0（'index'が'*'より優先）
    print(tg.switch_lit("char", 1, index=1))  # インデックス 1（'index'で指定）

example()
# == 出力 ==
# A
# B
# A
# B
```

```python
tg = Triggon({"A": True, "B": False})

def sample():
    # いずれかのラベルが有効なら、新しい値が適用されます。
    # 両方が有効な場合は、先に指定された方が優先されます。
    x = tg.switch_lit(["A", "B"], None)

    print(x)

sample()            # Output: None 

tg.set_trigger("A") # Output: True
sample()

tg.set_trigger("B") # Output: True
sample()
```

---

### switch_var
`self, label: str | dict[str, Any], var: Any = None, /,`  
`*, index: int = None`  
`-> Any`

指定されたラベルとインデックスで変数を登録します。  
ラベルが有効の場合、値を切り替えます。  
変数がすでに登録されている場合は、値の切り替えは `set_trigger()` によって処理されます。  

**対応しているのはグローバル変数とクラス変数で、ローカル変数には対応していません。**  
クラス変数をグローバルスコープから登録した場合は `InvalidClassVarError` が発生します。

単一のラベルで渡された場合のみ引数の値を返し、それ以外は `None` を返します。  
戻り値が `TrigFunc` クラスで遅延実行されてる関数の場合、  
それを自動的に実行しその戻り値を返します。

また、インデックスを指定するために、接頭辞として `*` を使うこともできます。  
たとえば、`"label"` はインデックス 0 を、`"*label"` はインデックス１を指します。
接頭辞以外の場所で使われた `*` はインデックスとして認識されないので、無視されます。
キーワード引数と `*` 両方が指定されている場合は、**キーワード引数の方が優先されます。**  

複数のラベルにそれぞれ違うインデックスを指定したい場合は、`*` を使ってください。

```python
import random

from triggon import Triggon

tg = Triggon({
    "level_1": ["ノーマル", 80],
    "level_2": ["レア", 100],
    "level_3": ["伝説の", 150],
})

level = None
attack = None

def spin_gacha():
    items = ["level_1", "level_2", "level_3"]
    result = random.choice(items)

    tg.set_trigger(result)

    tg.switch_var(result, level)
    tg.switch_var(result, attack, index=1)

    # 出力はランダムに変わります。
    # 例: result = "level_2"の場合
    print(f"{level}ソードを取得しました！") # 出力例: レアソードソードを取得しました！
    print(f"攻撃力: {attack}")    # 出力例: 攻撃力: 100 

spin_gacha()
```

また、１つの変数に対して複数の設定値に切り替えることも可能です。

```python
import math

from triggon import Triggon, TrigFunc

F = TrigFunc()
tg = Triggon("var", new=["ABC", True, F.math.sqrt(100)])

x = None

tg.set_trigger("var")

value = tg.switch_var("var", x)
print(value) # 出力: "ABC"

tg.set_trigger("var", index=1)
print(x)     # 出力: True

# 返り値が `TrigFunc` によって遅延されてる関数の場合、
# set_trigger()は自動実行はしません
tg.set_trigger("var", index=2)
print(x) # 出力: <function TrigFunc...>

# その場合は、自分で実行必要があります
if tg.is_triggered("var"):
    print(x()) # 出力: 10.0

# switch_var()の場合は、自動で実行しその値を返します
value = tg.switch_var("var", x, index=2)
print(value) # 出力: 10.0
```

> **Notes:**
> 値の更新は基本的に `set_trigger()` が呼ばれたときに行われます。  
> ただし初回のみ、`switch_var()` によって対象変数が登録されていない限り、値は変化しません。  
> その場合、値の変更は `switch_var()` で行われます。  
> 一度登録されれば、その後の `set_trigger()` 呼び出しで即座に値が更新されます。　
>
> 一部の実行環境では、`switch_var()` の呼び出しを静的に検出できず、  
> エラーになることがあります（例：Jupyter、REPLなど）。
>
> この関数では、ラベルおよび `index` 引数にリテラル値・変数・属性チェーン以外を指定すると、
> `InvalidArgumentError` が発生します。

---

### is_registered
`self, *variable: str`  
`-> bool | list[bool] | tuple[bool, ...]`

指定された変数ごとに、登録済みかどうかを `True` または `False` で返します。  
返り値の型は渡された引数によって変わります。

渡された引数が変数ではない場合、 `InvalidArgumentError` が発生します。

```python
tg = Triggon("var", None)

@dataclass
class Sample:
    x: int = 0
    y: int = 0
    z: int = 0

    def func(self):
        tg.switch_var("var", (self.x, self.z))
        print(tg.is_registered(["self.y", "self.z"]))

smp = Sample()
smp.func() # 出力: [False, True]

print(tg.is_registered("smp.x"))                # 出力: True
print(tg.is_registered("Sample.x", "Sample.y")) # 出力: [True, False]
```

---

### revert
`self, label: str | list[str] | tuple[str, ...] = None, /,`  
`*,`  
`all: bool = False,`  
`disable: bool = False,`  
`cond: str = None,`  
`after: int | float = None`  
`-> None`

指定されたラベルを無効化して、元の値に戻します。

この状態は、次に `set_trigger()` が呼び出されるまで有効です。  
指定されたラベルに関連付けられたすべての値が、元に戻されます。

#### ***all***
`True` に設定すると、すべてのラベルを無効にします。

### ***disable***
`True` に設定すると、すべてのラベルを永続的に無効にします。

この状態のラベルは、`set_trigger()` で有効化されません。

```python
tg = Triggon("flag", new="有効状態")

def sample():
    tg.set_trigger("flag") # Activate "flag" on each call

    x = tg.switch_lit("flag", org="無効状態")
    print(x)

sample() # 出力: 有効状態

# The effect persists until the next call to set_trigger()
tg.revert("flag")
sample() # 出力: 有効状態

# Permanently disable "flag"
tg.revert("flag", disable=True)
sample() # 出力: 無効状態
```

#### ***cond***
ラベルを無効にする条件を設定します。

> **⚠️ Note:**  
> この引数の処理には内部的に `eval()` を使用します。  
> **比較式のみ許可**されています（例: `x > 0 > y`, `value == 10`）。  
> 単体のリテラル値、または変数が渡された場合、  
> 値が `ブール値` 以外の時 `InvalidArgumentError` が発生します。  
> 関数呼び出しの場合も同様です。

#### ***after***
ラベルを無効化するまでの遅延時間を秒数で指定します。  
遅延中に再度指定された場合は上書きされずに、最初の秒数が維持されます。

> **⚠️ Note:**  
> 実際の実行は、指定した時間より **およそ 0.011 秒後** に行われます。

```python
from dataclasses import dataclass

from triggon import Triggon

tg = Triggon("hi", new="こんにちは")

@dataclass
class User:
    name: str = "Guest"
    init_done: bool = False

    def initialize(self):
        # 初回の挨拶用にトリガーをセット
        tg.set_trigger("hi")
        self.init_done = True
        self.greet()

    def greet(self):
        msg = tg.switch_lit("hi", org="おかえりなさい")
        print(f"{msg}, {self.name}!")

    def entry(self):
        if self.init_done:
            self.greet()
        else:
            self.initialize()
            tg.revert("hi")  # 値を元に戻す

user = User()
user.entry()  # 出力: こんにちは, Guest!
user.entry()  # 出力: おかえりなさい, Guest!
```

```python
tg = Triggon({"name": "太郎", "state": True})

@dataclass
class User:
    name: str = None
    online: bool = False

    def login(self):
        # 各ラベルに変数を設定
        tg.switch_var({"name": self.name, "state": self.online})
        tg.set_trigger(["name", "state"])

user = User()
print(f"User name: {user.name}\nOnline: {user.online}")
# == Output ==
# User name: None
# Online: False

user.login()
print(f"User name: {user.name}\nOnline: {user.online}")
# == Output ==
# User name: 太郎
# Online: True
```

---

### exit_point
`self, func: TrigFunc`  
`-> Any`

`trigger_return()` によって早期リターンで抜ける関数の出口を設定します。  
`func` 引数には、対象関数をラップした `TrigFunc` インスタンスを渡す必要があります。

> **Note:** `trigger_return()`が実行されない場合は、この関数を使用する必要はありません。

---

### trigger_return
`self, label: str | list[str] | tuple[str, ...], /,`  
`ret: Any = ...,`  
`*, index: int = None`  
`-> Any`

指定されたいずれかのラベルが有効な場合に、早期リターンを発動させます。  
返す値はインスタンス作成時に設定しておく必要があります。  
戻り値が必要がない場合は、`None` またはラベルのみ渡してください（辞書型でない場合のみ）。

キーワード引数 `ret` を使って戻り値を設定することもできます。  
その場合、**初期化時に設定された値は無視され、その値が返されます**。  
動的に戻り値を設定したい場合に使用してください。 

戻り値が `TrigFunc` クラスで遅延実行されてる関数の場合、  
それを自動的に実行しその戻り値を返します。

```python
from triggon import Triggon, TrigFunc

tg = Triggon("ret", None)

def sample(num):
    added = num + 5
    tg.set_trigger("ret", cond="added < 10")

    # 'added'が10より小さい場合、早期リターン
    tg.trigger_return("ret")

    result = added / 10
    return result

F = TrigFunc() # 遅延用の変数

result = tg.exit_point(F.sample(10))
print(result) # 出力: 1.5

result = tg.exit_point(F.sample(3))
print(result) # 出力: None
```

```python
tg = Triggon("skip") # 戻り値が必要ない場合はラベルのみ渡しても問題ありません
F = TrigFunc()

def sample():    
    # "skip"が有効な場合、指定の関数を呼んで、
    # 早期リターンと一緒にその戻り値を返す
    ret_value = tg.trigger_func("skip", F.func())
    tg.trigger_return("skip", ret=ret_value)

    print("戻り値なし")

def func():
    return "戻り値あり"

value = sample()
print(value)
# == 出力 ==
# 戻り値なし
# None

tg.set_trigger("skip") # "skip"を有効にする
value = tg.exit_point(F.sample())
print(value)
# == 出力 ==
# 戻り値あり
```

---

### trigger_func
`self, label: str | list[str] | tuple[str, ...], /,`  
`func: TrigFunc`  
`-> Any`

指定されたいずれかのラベルが有効の場合に、関数を呼び出します。  
`func` 引数には、対象の関数をラップした `TrigFunc` インスタンスを渡す必要があります。

ラベルはインスタンス作成時に登録しておく必要がありますが、  
設定した値が返されることはないため、どんな値でも正常に動作します。   
またはラベルのみ渡してください（辞書型でない場合のみ）。  
**対象の関数が値を返す場合は、その値が返されます。**

```python
from triggon import Triggon, TrigFunc

tg = Triggon({
    "skip": None,
    "call": None,
})

def func_a():
    tg.set_trigger(all=True) # 全てのラベルを有効にする

    print("'call'フラグが有効なら、func_b()が呼ばれます。")

    tg.trigger_func("call", F.func_b())

    print("このメッセージは出力されないかも。")


def func_b():
    print("func_b()に到達！")
    tg.trigger_return("skip")

F = TrigFunc()
tg.exit_point("skip", F.func_a())
# == 出力 ==
# 'call'フラグが有効なら、func_b()が呼ばれます。
# func_b()に到達！
```

---

### TrigFunc
このクラスは関数の実行を遅延させるために使います。  
引数なしでインスタンスを作成し、その変数を対象の関数にラップして利用してください。

既存ライブラリのほとんどの関数や自作関数を遅延できますが、  
インスタンスメソッドには対応していません。

> ⚠️ **注意:**  
> `TrigFunc` では、インスタンスを生成してすぐにメソッドをチェーン呼び出しすることはできません  
> （例: `F.Sample(10).method()`）。  
>  
> まず通常どおりインスタンスを生成して変数に代入し、  
> その変数を通じて `TrigFunc` からメソッドを呼び出してください。  
> （例: `smp = Sample(10)` → `F.smp.method()`）

---

### エラー

#### ***InvalidArgumentError***
引数の数、または使い方に誤りがある場合に発生します。

#### ***InvalidClassVarError***
`switch_var()`でクラス変数をグローバルスコープから登録した場合に発生します。

#### ***MissingLabelError***
設定されたラベルが登録されていない場合に発生します。

## ライセンス
このプロジェクトは MIT ライセンスの下で公開されています。　
詳細は LICENSE をご覧ください。

## 開発者
Tsuruko  
GitHub: [@tsuruko12](https://github.com/tsuruko12)  
X: [@12tsuruko](https://x.com/12tsuruko)
