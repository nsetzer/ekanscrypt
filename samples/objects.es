

newAnimal = (name) => {
    obj = {
        "name": name,
        "speak": () => {
            print(obj["name"])
        }
    }
    return obj;
}

newCat = () => {
    obj = newAnimal("Cat")
    obj["memeable"] = true
    return obj
}

animal = newAnimal("frog")
animal->speak()

cat = newCat()
cat->speak()

print(cat)