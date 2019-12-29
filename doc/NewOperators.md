


### Property Drill

```python
    x->0
    x->y
```

The property drill `x->y` is equivalent to `x["y"]`.
That is, it implements a subcript operator. The Right Hand Side
can be either an unquoted string, or a number. When the containment
test fails (i.e. `y in x`) hasattr/getattr are used as a backup.

The property drill has an additional feature, in that it returns
None when the property does not exist or the Left Hand Side is None.

```python

    a = [1,2,3]

    a->0 # 1
    a->4 # None

    b = {"year": 1970, "month": 1, "day": 1}

    b->year # 1970
    b->time # None

```

### Optional Chaining

```python
    x?.y
    x?.()
    x?.[]
```

Optional chaining performs null checking before resolving an operation.
When used to access a property `x?.y` the property y is returned if the value
of x is not None, otherwise None is returned. Similarly function calls and subscript
access `x?.()` will only be performed if the attribute x is not None.


```python

    a = None
    a?.push # returns None, since a is None
    a?.()   # return None, since a is None
    a?.[]   # return None, since a is None

    b = list()
    b?.push # raises an exception since list does not define push


```

Optional Chaining and Property Drill can be combined

```python
a = [1,2,3]


a->push?.(4) # returns None
a->append?.(4) # successfully appends value 4

```

the alternative would look something like this:

```python
if hasattr(a, 'append'):
    if a.append is not None:
        a.append(4)
```

This example is a bit contrived since a list will always have append defined
