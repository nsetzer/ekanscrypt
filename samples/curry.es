

add = (x, y) => {x + y}

add5 = (x) => add(x, 5)

newCounter = () => {
    x = 0;
    return () => {return ++x;}
}

print(add5(12))

counter1 = newCounter()

print(counter1(), counter1(), counter1())

counter2 = newCounter()

print(counter1(), counter2(), counter1())

