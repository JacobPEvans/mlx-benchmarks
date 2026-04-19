{
  description = "mlx-benchmarks development environment (Apple Silicon only)";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-25.11-darwin";
    devenv = {
      url = "github:cachix/devenv";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, devenv, ... }@inputs:
    let
      # MLX benchmark tools only ship aarch64 wheels
      systems = [ "aarch64-darwin" ];
      forAllSystems =
        f:
        nixpkgs.lib.genAttrs systems (
          system:
          f {
            pkgs = nixpkgs.legacyPackages.${system};
          }
        );
    in
    {
      devShells = forAllSystems (
        { pkgs }:
        {
          default = devenv.lib.mkShell {
            inherit inputs pkgs;
            modules = [
              {
                languages.python = {
                  enable = true;
                  uv = {
                    enable = true;
                    sync.enable = true;
                  };
                };

                enterShell = ''
                  # Set HF_HOME: use external volume if mounted, otherwise fall back
                  if [ -d "/Volumes/HuggingFace" ] && [ -w "/Volumes/HuggingFace" ]; then
                    export HF_HOME="/Volumes/HuggingFace"
                  else
                    export HF_HOME="''${XDG_CACHE_HOME:-''${HOME}/.cache}/huggingface"
                    mkdir -p "''${HF_HOME}"
                  fi
                  echo "mlx-benchmarks environment ready ($(python3 --version))"
                '';
              }
            ];
          };
        }
      );
    };
}
