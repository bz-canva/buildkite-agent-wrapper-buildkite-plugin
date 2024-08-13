with import <nixpkgs> {};

runCommand "dummy" {
    buildInputs = [
        python311
    ];
} ""
