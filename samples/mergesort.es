
merge(left, right) => {
    result = [];
    while left && right {
        if left[0] <= right[0] {
            result.append(left.pop(0));
        } else {
            result.append(right.pop(0));
        }
    }
    while left {
        result.append(left.pop(0));
    }
    while right {
        result.append(right.pop(0));
    }
    return result;
}

mergesort(lst) => {
    if len(lst) <= 1 {
        return lst;
    }

    m = len(lst)//2;
    left = lst[:m];
    right = lst[m:];

    left = mergesort(left)
    right = mergesort(right)
    return merge(left, right);
}

main() => {
    lst = [1,0,2,9,3,8,4,7,5,6]
    print("input :", lst)
    print("output:", mergesort(lst))
}


