

# find sets of words that are translateable into 'hello world'

dict = '/usr/share/dict/american-english'

# return the number of unique characters in a string
count_unique = (word) => {
    return len(set(word))
}

# return true if a word is all ascii lowercase
is_ascii = (word) => {
    ascii = "abcdefghijklmnopqrstuvwxyz";
    for c : word {
        if (ascii.find(c)<0) {
            return false;
        }
    }
    return true;
}

# return true if a word matches the pattern of 'hello'
rule1 = (word) => {
    return len(word) == 5 && is_ascii(word) && count_unique(word) == 4 && word[2] == word[3];
}

# return true if a word matches the pattern of 'world'
rule2 = (word) => {
    return len(word) == 5 && is_ascii(word) && count_unique(word) == 5;
}

# return true if the pair of words matches the pattern of 'hello world'
rule3 = (word1, word2) => {
    return (word1[3] == word2[3]) && (word1[4] == word2[1]) && count_unique(word1 + word2) == 7;
}

# create a pipeline node that prints out lines matching the given rule
find = (rule) => {
    return Proc.TextNode((stream) => {
        while (line = stream.stdin.readline2()) {
            if rule(line) {
                stream.stdout.writeline2(line)
            }
        }
    })
}

pipeline = exec cat ${dict} |> find(rule1);
_, out1, _ = pipeline.run();

pipeline = exec cat ${dict} |> find(rule2);
_, out2, _ = pipeline.run();

for word1 : out1.split("\n") {
    for word2 : out2.split("\n") {
        if (word1 && word2 && rule3(word1, word2)) {
            print(word1, word2);
        }
    }
}

# a process node which simulates the command 'tr'
# translate characters in set1 into characters from set2

tr = (set1, set2) => {
    return Proc.TextNode((stream) => {
        while (c = stream.stdin.read(1)) {
            index = set1.find(c);
            if (index < 0) {
                stream.stdout.write(c);
            } else {
                stream.stdout.write(set2[index]);
            }
        }
    })
}

exec echo bunny hymns |> exec tr hbunyms whelord;

exec echo bunny hymns |> tr('hbunyms','whelord');