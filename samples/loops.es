
if(true){
    print("true");
}

if(false){
    print("false");
}

if(false){
    print("true");
} else {
    print("false");
}

if(false){
    print("false");
} else if (true) {
    print("true");
}


print("-");
for(x:[1,2,3]){
    if(x==2){
        break;
    }
    print(x);
}

print("-");
for(x:[1,2,3]){
    if(x==2){
        continue;
    }
    print(x);
}

print("-");
x=0;
while(x<5){
    print(x)
    break;
}

print("-")
x=0;
while(x<5){
    print(x);
    x += 1;
    if(x==3){
        continue;
    }
}

