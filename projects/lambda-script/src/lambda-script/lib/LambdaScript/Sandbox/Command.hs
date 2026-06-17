module LambdaScript.Sandbox.Command
  ( SandboxCommand(..)
  , OnepushOptions(..)
  , optShip
  , optInitFromDir
  , parseCommand
  , helpText
  ) where

data SandboxCommand
  = SandboxHelp
  | SandboxOnepush OnepushOptions
  | SandboxLand FilePath
  deriving (Eq, Show)

data OnepushOptions =
  OnepushOptions Bool (Maybe FilePath)
  deriving (Eq, Show)

optShip :: OnepushOptions -> Bool
optShip (OnepushOptions ship _) = ship

optInitFromDir :: OnepushOptions -> Maybe FilePath
optInitFromDir (OnepushOptions _ dir) = dir

parseCommand :: [String] -> Either String SandboxCommand
parseCommand args =
  case args of
    [] -> Right SandboxHelp
    ["help"] -> Right SandboxHelp
    "onepush" : rest -> SandboxOnepush <$> parseOnepush rest
    ["land", patch] -> Right (SandboxLand patch)
    "land" : _ -> Left "land expects exactly one patch path"
    _ -> Left "unsupported command"

parseOnepush :: [String] -> Either String OnepushOptions
parseOnepush = go False Nothing
  where
    go ship initDir args =
      case args of
        [] -> Right (OnepushOptions ship initDir)
        "--ship" : rest
          | ship -> Left "duplicate --ship"
          | otherwise -> go True initDir rest
        "--init-from-dir" : dir : rest
          | maybe False (const True) initDir -> Left "duplicate --init-from-dir"
          | null dir -> Left "--init-from-dir requires a non-empty directory"
          | otherwise -> go ship (Just dir) rest
        ["--init-from-dir"] -> Left "--init-from-dir requires a directory"
        flag : _
          | take 2 flag == "--" -> Left ("unsupported flag: " ++ flag)
          | otherwise -> Left ("unexpected argument: " ++ flag)

helpText :: String
helpText =
  unlines
    [ "sandbox commands:"
    , "  cabal run sandbox -- onepush"
    , "  cabal run sandbox -- onepush --ship"
    , "  cabal run sandbox -- onepush --init-from-dir <directory>"
    , "  cabal run sandbox -- onepush --ship --init-from-dir <directory>"
    , "  cabal run sandbox -- land <patch.json>"
    , ""
    , "sandbox.json fields:"
    , "  tool_root: trusted tooling root containing the generated access buttons"
    , "  button: target button stem, e.g. lambda-script-edd"
    ]
