# triggon

[![PyPI](https://img.shields.io/pypi/v/triggon)](https://pypi.org/project/triggon/)
![Python](https://img.shields.io/pypi/pyversions/triggon)
![Python](https://img.shields.io/pypi/l/triggon)
![Package Size](https://img.shields.io/badge/size-25.1kB-lightgrey)

# 概要
特定のトリガーポイントで単体または複数の値を動的に切り替えるライブラリです。

> ⚠️ **このライブラリは現在ベータ版です。  
> バグが存在する可能性や、将来的にAPIが変更される可能性があります。**

> ⚠️ 次回のアップデートで、`alter_var()`および`alter_literal()`の関数名は、  
> それぞれ `switch_var()` および `switch_lit()` に変更されました。  
> ベータ期間中は互換性のため、従来の関数名も引き続き使用可能です。

## 目次
- [インストール方法](#インストール方法)
- [使い方](#使い方)
- [ライセンス](#ライセンス)
- [開発者](#開発者)

## 特徴
- 単一のトリガーポイントで複数の値をまとめて切り替え可能
- if や match 文は不要
- リテラル値・変数の両方を切り替え可能
- 任意の戻り値付きで早期リターンが可能
- トリガー時に他の関数へ自動ジャンプ可能

## 計画中の追加機能
- 値や関数以外のコードの動きも切り替えられるようにしたいと考えています

## 追加予定の機能
- タイマーによる遅延トリガー制御のサポート

## インストール方法
```bash
pip install triggon
```

## 使い方
このセクションでは、各関数の使い方を説明します。

### Triggon
`Triggon(self, label: str | dict[str, Any], /, new: Any=None, *, debug: bool=False)`

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
    "seq2": [1, 2, 3],   # インデックス0, 1, 2に1, 2, 3 を設定
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

tg = Triggon("mode", new=True) # 'mode' ラベルのインデックス0に True を設定

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

ラベルの状態をリアルタイムで追跡したい場合は、`debug` キーワードに `True` を指定してください。　

> ⚠️ **Note:** 
`*` プレフィックス付きのラベルは初期化時には使用できず、`InvalidArgumentError` が発生します。　

### set_trigger
`def set_trigger(self, label: str | list[str] | tuple[str, ...], /, *, cond: str=None) -> None`

指定したラベルにトリガーを設定し、次回の呼び出しで値が更新されるようにします。  
インデックスに関係なく、そのラベルに関連付けられたすべての値が変更されます。  
`label` 引数には、文字列またはラベル名のリスト／タプルを渡すことができます。 

キーワード引数 `cond` には比較式による条件を設定できますが、`if` などの制御構文は使用できません。

なお、`revert()` を使って無効化されたラベルに対しては、フラグは変更されません。

```python
from triggon import Triggon

tg = Triggon({
    "milk": 130,
    "banana": 90,
    "msg": "本日は牛乳の特売日です！",
})

def example():
    msg = tg.switch_lit("msg", org="本日は通常通りの営業です。")
    print(msg)

    milk = tg.switch_lit('milk', 200)
    banana = tg.switch_lit('banana', 120)

    print(f"牛乳: {milk}円")
    print(f"バナナ: {banana}円")

example()
# == 出力 ==
# 本日は通常通りの営業です。
# 牛乳: 200円
# バナナ: 120円

tg.set_trigger(["milk", "msg"]) # 'milk'と'msg'にトリガーを設定

example()
# == 出力 ==
# 本日は牛乳の特売日です！
# 牛乳: 130円
# バナナ: 120円
```


```python
tg = Triggon("msg", "呼びましたか？")

def sample(print_msg: bool):
    # print_msgがTrueの場合に"msg"のフラグを有効にする
    tg.set_trigger("msg", cond="print_msg")

    # "msg"フラグが有効な場合、テキストを出力する
    print(tg.switch_lit("msg", ""))

sample(False) # Output:
sample(True)  # Output: 呼びましたか？ 
```

> ⚠️ **Note:** 
この関数では内部で`eval()`を使用しています。
ただし、比較式（例: `x > 0 > y`, `value == 10`）のみが許可されており、
それ以外の式が指定された場合は`InvalidArgumentError`が発生します。

### switch_lit (alter_literal)
`def switch_lit(self, label: str | list[str] | tuple[str, ...], /, org: Any, *, index: int=None) -> Any`

ラベルのフラグが有効の場合、リテラル値を変更します。    
この関数は `print()` の中で直接使うこともできます。  　  
`label` に辞書を使う場合、`index` キーワードは使用できません。

```python
from triggon import Triggon

tg = Triggon("text", new="After") 

def example():
    text = tg.switch_lit("text", org="Before", index=0)
    print(text)  

    # print内に直接書くこともできます:
    # print(tg.switch_lit('text', 'Before'))

    tg.set_trigger("text")

example() # 出力: Before
example() # 出力: After
```

また、インデックスを指定するために、接頭辞として `*` を使うこともできます。  
たとえば、`"label"` はインデックス 0 を、`"*label"` はインデックス１を指します。

`index` キーワードと `*` の接頭辞は、どちらも使用可能です。  
両方が指定されている場合は、キーワード引数の方が優先されます。  
接頭辞以外の場所で使われた `*` にインデックスとして認識されないので、無視されます。

> **Note:**  複数のインデックスを扱う場合は、可読性のため`index`キーワードの使用を推奨します。

```python
# インデックス 0 に 'A' を、インデックス 1 に 'B' を設定
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

> **Note:**   
複数のラベルが渡され、その中で複数のフラグが有効になっていた場合は、  
配列内でインデックスの早いラベルが優先されます。
`index`引数が指定されてた場合は、全てのラベルに適用されます。

### switch_var (alter_var)
`def switch_var(self, label: str | dict[str, Any], var: Any=None, /, *, index: int=None) -> None | Any`

トリガーが有効な場合、変数の値を直接変更します。  
**対応しているのはグローバル変数とクラス属性で、ローカル変数には対応していません。**

複数のラベルと変数を辞書形式で渡すこともできます。  
その場合、`index` キーワードは使用できません。  
対象インデックスが1以上の場合は、  
ラベルに対応する接頭辞として `*` を追加してください（例：index 1 → *label、index 2 → **label）。

**単一のラベルで渡された場合のみ、引数の値を返します。**  
辞書型で渡された場合は`None`を返します。

> **Note:**  
もしインデックスが大きくなる場合は、  
個別に関数を呼び出し、`index` キーワードを使って指定することを推奨します。

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
    # 例: result = 'level_2'の場合
    print(f"{level}ソードを取得しました！") # 出力例: レアソードソードを取得しました！
    print(f"攻撃力: {attack}")    # 出力例: 攻撃力: 100 

spin_gacha()
```

```python
from dataclasses import dataclass

from triggon import Triggon

tg = Triggon("even", [0, 2, 4])

@dataclass
class Example:
    a: int = 1
    b: int = 3
    c: int = 5

    def change_field_values(self, change: bool):
        if change:
            tg.set_trigger("even")

        tg.switch_var({
            "even": self.a,   # インデックス 0
            "*even": self.b,  # インデックス 1
            "**even": self.c, # インデックス 2
        })

exm = Example()

exm.change_field_values(False)
print(f"a: {exm.a}, b: {exm.b}, c: {exm.c}")
# 出力: a: 1, b: 3, c: 5

exm.change_field_values(True)
print(f"a: {exm.a}, b: {exm.b}, c: {exm.c}")
# 出力: a: 0, b: 2, c: 4
```

また、１つの変数に対して複数の設定値に切り替えることも可能です。

```python
tg = Triggon({
    "flag": [True, False],
    "num": [0, 100],
})

@dataclass
class Sample:
    flag: bool = None
    num: int = None

    def sample(self, label: str, label_2: str):
        tg.switch_var({label: self.flag, label_2: self.num})

        print(f"flag: {self.flag}, num: {self.num}")

s = Sample()
tg.set_trigger(["flag", "num"])

s.sample("flag", "num")   # 出力: flag: True, num: 0
s.sample("*flag", "*num") # 出力: flag: False, num: 100
```

> **Notes:**
> 値の更新は基本的に `set_trigger()` が呼ばれたときに行われます。  
> ただし初回のみ、`switch_var()` によって対象変数が登録されていない限り、値は変化しません。  
> その場合、値の変更は `switch_var()` で行われます。  
> 一度登録されれば、その後の `set_trigger()` 呼び出しで即座に値が更新されます。　
>
> 一部の実行環境では、alter_var や switch_var の呼び出しを静的に検出できず、  
> エラーになることがあります（例：Jupyter、REPLなど）。
>
> この関数では、ラベルおよび`index`引数にリテラル値・変数・属性チェーン以外を指定すると、
> `InvalidArgumentError`が発生します。

### revert
`def revert(self, label: str | list[str] | tuple[str, ...]=None, /, *, all: bool=False, disable: bool=False) -> None`

`switch_lit()` または `switch_var()` によって変更された値を、元の状態に戻します。  
全てのラベルの値を一括で戻したい場合は、キーワード引数`all`を`True`に設定してください。

この復元状態は、次に `set_trigger()` が呼び出されるまで有効です。  
指定されたラベルに関連付けられたすべての値が、インデックスに関係なく元に戻されます。

`disable` キーワードを `True` に設定すると、以降元の値が永続的に使用されます。

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

### exit_point
`def exit_point(self, label: str, func: TrigFunc, /) -> None | Any`

`trigger_return()` によって早期リターンで抜ける関数の出口を設定します。  
`func` 引数には、対象関数をラップした `TrigFunc` インスタンスを渡す必要があります。

`*` プレフィックス付きのインデックスも使用できますが、ここでは無視されます。

> **Note:** `trigger_return()`が実行されない場合は、この関数を使用する必要はありません。

### trigger_return
`trigger_return(self, label: str, /, ret: Any=None, *, index: int=None, do_print: bool=False) -> None | Any`

フラグが有効な場合に、早期リターンを発動させます。  
返す値は初期化時に設定しておく必要があります。  
何も返す必要がない場合は、`None` を設定してください。

`ret` に値を設定した場合、初期化時に設定された値は無視され、その値が返されます。  
辞書型でない場合は、値を設定しなくても正常に動作します。

キーワード引数 `do_print` を `True` にすると、リターン値を出力します。  
ただし、値が文字列でない場合は `InvalidArgumentError` が発生します。

```python
from triggon import Triggon, TrigFunc

# ラベルと早期リターン値の定義
tg = Triggon("skip", new="（お金が不足しています...）")
F = TrigFunc() # 対象関数を早期リターン用にラップ

def check_funds(money: int):
    if money < 300:
        tg.set_trigger("skip")

    print(f"現在の所持金：{money}G")
    board_ship()

def board_ship():
    print("船に乗るには300Gかかります。")

    # フラグが有効なら、早期リターンを実行し、値を表示
    tg.trigger_return("skip", do_print=True) 

    print("楽しい航海を！")  

tg.exit_point("skip", F.check_funds(500))
# == 出力 ==
# 現在の所持金：500G
# 船に乗るには300Gかかります。
# 楽しい航海を！

tg.exit_point("skip", F.check_funds(200))
# == 出力 ==
# 現在の所持金：200G
# 船に乗るには300Gかかります。
# （お金が不足しています...）
```

```python
tg = Triggon("zero")
F = TrigFunc()

def sample():
    num = get_number()

    # `num`が0の場合にラベル"zero"のフラグを有効にする
    tg.set_trigger("zero", cond="num == 0")

    # テキストを出力して早期リターン
    tg.trigger_return("zero", ret=f"{num} ...", do_print=True) 

    num_2 = get_number()

    print(f"The total number is {num + num_2}!")

def get_number():
    return random.randint(0, 10) 

tg.exit_point("zero", F.sample()) # The output is random!
```

### trigger_func
`def trigger_func(self, label: str, func: TrigFunc, /) -> None | Any`

フラグが有効の場合に、関数を呼び出します。  
`func` 引数には、対象の関数をラップした `TrigFunc` インスタンスを渡す必要があります。

ラベルは初期設定時に登録しておく必要がありますが、  
設定した値が返されることはないため、どんな値でも正常に動作します。  
また、辞書型を使用しない場合は、値を設定する必要はありません。  
**対象の関数が値を返す場合は、その値が返されます。**

ラベルに `*` プレフィックスをつけたインデックスも使用できますが、無視されます。

```python
from triggon import Triggon, TrigFunc

tg = Triggon({
    "skip": None,
    "call": None,
})
F = TrigFunc()

def example():
    tg.set_trigger(["skip", "call"]) # 早期リターンと関数呼び出しのフラグを有効にする

    print("“call”フラグが有効なら、example_2() にジャンプします。")

    tg.trigger_func("call", F.example_2()) # example_2() を呼び出す

    print("このメッセージは出力されないかも。")


def example_2():
    print("example_2() に到達！")
    tg.trigger_return("skip")

tg.exit_point("skip", F.example())
# == 出力 ==
# “call”フラグが有効なら、example_2() にジャンプします。
# example_2() に到達！
```

### TrigFunc
このクラスは、関数の実行を遅延させるためのラッパーです。  
引数なしでインスタンスを作成し、対象の関数をラップして使用できます。

> ⚠️ **Note:** 
このクラスを使う際は、必ず先にインスタンス（例：F = TrigFunc()）を作成してから使用してください。

### エラー
- `InvalidArgumentError`  
引数の数、型、または使い方に誤りがある場合に発生します。

- `MissingLabelError`
設定されたラベルが登録されていない場合に発生します。

## ライセンス
このプロジェクトは MIT ライセンスの下で公開されています。　
詳細は LICENSE をご覧ください。

## 開発者
Tsuruko　
GitHub: @tsuruko12　
X: @12tsuruko
