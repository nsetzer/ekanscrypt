
# create a 2 dimensional matrix

x = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
]

# loop until the target value is found
# break out of both loops
eprint(1)
for row : x {
    for value : row {
        print(value)
        if value == 1 {
            continue 1;
        } else if value == 5 {
            break 1;
        }
    }
}

# 28    LOAD_FAST 0          #
# 30    GET_ITER             #
# 32    FOR_ITER 44          # outer loop, continue 2 target
# 34    STORE_FAST 1         #
# 36    LOAD_FAST 1          #
# 38    GET_ITER             #
# 38    GET_ITER             #
# 40    FOR_ITER 34          # inner loop
# 42    STORE_FAST 2         #
# 44    LOAD_GLOBAL 0        #
# 46    LOAD_FAST 2          #
# 48    CALL_FUNCTION 1      #
# 50    POP_TOP              #
# 52    LOAD_FAST 2          #
# 54    LOAD_CONST 2         #
# 56    COMPARE_OP 2         #
# 58    POP_JUMP_IF_FALSE 64 #
# 60    JUMP_ABSOLUTE 32     # continue 2
# 62    JUMP_ABSOLUTE 74     #
# 64    LOAD_FAST 2          #
# 66    LOAD_CONST 6         #
# 68    COMPARE_OP 2         #
# 70    POP_JUMP_IF_FALSE 74 #
# 72    JUMP_ABSOLUTE 78     # break 2
# 74    JUMP_ABSOLUTE 40     # next inner
# 76    JUMP_ABSOLUTE 32     # next outer
# 78    LOAD_CONST 0         # break 2 target
# 80    RETURN_VALUE         #

#          LOAD_FAST                  # [s1]
#          GET_ITER                   # [g1]
# loop_1:  FOR_ITER      end__1       # [g1, v1]
#          STORE_FAST                 # [g1]
#          LOAD_FAST                  # [g1, v1]
#          GET_ITER                   # [g1, g2]
# loop_2:  FOR_ITER      end__2       # [g1, g2, v2]
#          STORE_FAST                 # [g1, g2]
#          ...
# cont_2:  JUMP_ABSOLUTE clean2

# break2:  JUMP_ABSOLUTE clean3
#          ...
#       :  JUMP_ABSOLUTE loop_2
# clean2:  POP_TOP              # continue 2
#          JUMP_ABSOLUTE loop_1 # continue 2 (happens to duplicate next)
# clean3:  POP_TOP
#          JUMP_ABSOLUTE cleanr 4
# end__2:  JUMP_ABSOLUTE loop_1 # end of loop
# clean1:  POP_TOP              # continue 2, level 2
#          JUMP_ABSOLUTE loop_1 # continue 2, level 2
# clean4:  POP_TOP              # break 2, level 2
#          JUMP_ABSOLUTE end_1  #
# end__1:  ...
