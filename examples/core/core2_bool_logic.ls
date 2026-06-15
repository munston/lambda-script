module CoreBoolLogic

both : bool -> bool -> bool
both a b = a && b

either : bool -> bool -> bool
either a b = a || b

inverse : bool -> bool
inverse ok = !ok

neither : bool -> bool -> bool
neither a b = not (a || b)

inside : i32 -> bool
inside x = x > 0 && x < 10

fallback : bool -> i32
fallback ok = if ok || false then 1 else 0

choice = true || false
