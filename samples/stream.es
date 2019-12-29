# this example demonstrates how the process pipe |> operator
# can be used with python/ekanscrypt objects.
# it creates a source, intermediate, and sink node which
# replactes the following bash syntax:
#     echo "source line 1" | tr 's' 'S' | cat -
# which could be re-written in ekanscrypt as:
#       exec echo "source line 1" | exec tr 's' 'S' | exec cat '-'
#
# This example can be written in ekanscrypt without the |> operator
# by doing the following transformation:
#
#       source() |> node() |> sink()
#
#       a = source()
#       b = node()
#       c = sink()
#
#       Proc.communicate(c(b(a()))
#

# create a processor node which generates data
# the source is null since this is the first node in the pipeline
# the destination is the next stream in the pipeline
source = () => {
    return Proc.Node((stream) => {
        stream.stdout.write(b"source line 1\n");
        stream.stdout.write(b"source line 2\n");
        stream.stdout.write(b"source line 3\n");
    })
}

# create an intermediate node which transforms data
# the source is the previous stream in the pipeline
# the destination is the next stream in the pipeline
# read from the output of the source and write to
# the input of the destination
node = () => {
    return Proc.Node((stream) => {
        while (buf = stream.stdin.read(512)) {
            buf = buf.replace(b"s", b"S")
            stream.stdout.write(buf);
        }
    })
}

# create a sink node which terminates the pipeline
# the source is the previous stream in the pipeline
# the destination is null since this is the last node in the pipeline
sink = () => {
    return Proc.Node((stream) => {
        while (buf = stream.stdin.read(512)) {
            stream.stdout.write(buf);
        }
    })
}

# execute the pipeline

source() |> node() |> sink()

# try replacing any stage with a shell command

#source() |> exec tr 's' 'S' |> exec cat '-';
#exec echo "source line 1" |> node() |> exec cat '-';
#exec echo "source line 1" |> exec tr 's' 'S' |> sink();

