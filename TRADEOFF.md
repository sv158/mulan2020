## 推敲

木兰诗云：

```
东市买骏马
西市买鞍鞯
南市买辔头
北市买长鞭
```

因此复兴木兰的主要手段是致敬

首先是向木兰致敬，刘雷博士为避免像Python一样，空集和空字典都是 `{}`，
采用 `{:}` 表示空字典。这让代码中的空字典，和用 `print` 函数显示的空字
典不一致。因此，木兰2020反其道而行，用 `{/}` 表示空集，长的更像数学符
号。刘雷博士对Lua情有独钟，因此在木兰2020中，字符串不像Python那样用引
号，而是向Lua致敬，`{[` 和 `]}`中间才是字符串。

随着NumPy/SciPy兴起，越来越多Fortran用家转投Python阵营。为了吸引
Fortran用家，木兰2020向Fortran致敬，函数名前后各加一个点，就可以当运算
符用。比如

```
let x = .sum. [1,2,3];
```

相当于Python

```
x = sum([1,2,3])
```

因为任意函数都可能成为运算符，很难定义出一个不容易用错的优先级。因此，
木兰2020需要向Pony致敬，运算符没有优先级的概念，要用两个运算符必须加括
号。

同时木兰2020还将支持APL风格的运算符。比如

```
let x = .(.sum. / .len.). [1,2,3,4];
```

相当于Python

```
x = (lambda a: sum(a)/len(a))([1,2,3,4])
```

因为运算符占用了 `.` ，木兰2020将向PHP致敬，用 `->` 代表Python中的 `.` 。

```
let x = a->b;
```

相当于Python

```
x = a.b
```


Eich[曾经](https://brendaneich.com/2006/02/python-and-javascript/)提到
过

> Given the years of development in Python and similarities to
> ECMAScript in application domains and programmer communities, we
> would rather follow than lead. By standing on Python

三十年河东三十年河西，鉴于ES6已经全面超过Python了，木兰2020将不设上限
向ECMAScript致敬


木兰2020首先抄袭Object Matching

```
let object {a, b:y, c=3} = x;
```

相当于Python

```
assert isinstance(x, object)
a = x.a
y = x.b
c = x.c if hasattr(x, "c") else 3
```

为了保持和Object Matching对称，木兰2020还将抄袭Property Shorthand。

```
f {a, b, c: 1};
```

相当于Python

```
f (a=a, b=b, c=1)
```


木兰2020将向Python的老祖宗SETL致敬，抄袭case语句

```
case a
when (int(x),) if x > 1:
  print(x);
else:
  print(a);
end
```

木兰2020将保留Python中的 `is` ，比如

```
let x is object {y} = a
```

相当于Python

```
x = a
assert isinstance(a, object)
y = a.y
```


木兰2020将向Erlang致敬，沿用其作用域规则，即在模式中出现的变量，会从当
前函数的作用域开始逐层往外找，若找不到会在当前函数的作用域声明一个新的
局部变量。

```
a := 0;
def f()
  a := 1;
end
f();
print(a);
```

输出的是

```
1
```

采用了这样的作用域规则，若像Python一样，有些全局变量是未经声明就已经存
在，将无法判断模式中出现的变量是否应该声明局部变量。木兰2020将向Rust致
敬，抄袭其模块语法。模块名后面加 `::` 就能直接得到这个模块，比如
`sys::` 表示 `sys` 模块，`os::` 表示 `os` 模块，如果省略模块名，则表示
`builtins` 模块。