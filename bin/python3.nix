with import <nixpkgs> {};

runCommand "dummy" {
    buildInputs = [
        python311
        python311Packages.ruamel_yaml
    ];
} ""
