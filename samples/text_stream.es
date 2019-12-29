
# this is the same example as stream.es
# TextNode is used instead of Node to allow
# reading and writing utf-8 text instead

source = () => {
    return Proc.TextNode((stream) => {
        stream.stdout.write("source line 1\n");
        stream.stdout.write("\n");
        stream.stdout.write("source line 3\n");
    })
}

# readline2 reads every line from the input
# but only returns if the line is not empty
# it also does not return the terminal new line char
# an empty string is returned when the file is exhausted
# writeline2 writes the line and automatically adds a new line
node = () => {
    return Proc.TextNode((stream) => {
        while (line = stream.stdin.readline2()) {
            line = line.replace("s", "S")
            stream.stdout.writeline2(line);
        }
    })
}

sink = () => {
    return Proc.TextNode((stream) => {
        while (line = stream.stdin.readline()) {
            stream.stdout.write(line);
        }
    })
}

# execute the pipeline

source() |> node() |> sink()

# try replacing any stage with a shell command

#source() |> exec tr 's' 'S' |> exec cat '-';
#exec echo "source line 1" |> node() |> exec cat '-';
#exec echo "source line 1" |> exec tr 's' 'S' |> sink();

