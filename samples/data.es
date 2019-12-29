
# eventually takes arguments such as
# col=[0,2]
# sep=None # or character


col = (col=0,sep=null) => {
    return Proc.TextNode((stream)=>{
        while (line = stream.stdin.readline2()) {
            parts = line.strip().split(sep);
            stream.stdout.writeline2(parts[col]);
        }
    })
}


exec cat 'samples/data.txt' |> col(sep=' ',col=1)
