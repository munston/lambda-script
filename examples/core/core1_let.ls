module Core1Let

square_plus : i32 -> i32 -> i32
square_plus x y = let xx = x * x in xx + y

clamp_min : i32 -> i32 -> i32
clamp_min floor x = let below = x < floor in if below then floor else x
