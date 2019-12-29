

copy(dst, src) => {

    i = len(src)
    while (i > 0) {
        switch (i%8) {
            case 0 {dst[i--] = src[i]}
            case 7 {dst[i--] = src[i]}
            case 6 {dst[i--] = src[i]}
            case 5 {dst[i--] = src[i]}
            case 4 {dst[i--] = src[i]}
            case 3 {dst[i--] = src[i]}
            case 2 {dst[i--] = src[i]}
            case 1 {dst[i--] = src[i]}
        }
    }

}


dst = [0] * 20
src = list(range(20))

copy(dst, src)

print(dst)