module Hat
  ( mainHat
  , fingerprintText
  , checkHatFile
  , emitHatFile
  ) where

import Control.Monad (unless, when)
import Data.Bits (xor, (.&.))
import Data.Char (isDigit, isSpace, ord, toLower)
import Data.List (isPrefixOf)
import Numeric (showHex)
import System.Directory (createDirectoryIfMissing, doesFileExist, makeAbsolute)
import System.Environment (getArgs)
import System.Exit (ExitCode(..), exitWith)
import System.FilePath ((</>), takeBaseName, takeDirectory, takeFileName)
import System.IO (hPutStrLn, stderr)
import System.Process (CreateProcess(..), createProcess, proc, waitForProcess)

-- Hat deliberately models only a tiny, auditable subset of batch-style wrapper
-- files: comments, directory changes, directory creation, and per-line command
-- invocation with positional argument forwarding. It is not a cmd.exe clone and
-- must not grow support for control-flow, fallback trees, redirection, pipes, or
-- ambient batch expansion. A select .bat can become .hat by extension change only
-- when every line already fits this strict subset and the first-line hash is set.
backendVersion :: String
backendVersion = "hat-backend-v3"

data HatFile = HatFile
  { hatPath :: FilePath
  , hatDeclaredHash :: String
  , hatCommands :: [HatCommand]
  } deriving (Eq, Show)

data HatCommand
  = HatCd String
  | HatMkdir String
  | HatExec String [String]
  deriving (Eq, Show)

mainHat :: IO ()
mainHat = do
  args <- getArgs
  case args of
    file:rest
      | ".hat" `isSuffixOfSimple` file -> runHatFile file rest
    _ -> hPutStrLn stderr "hat: expected FILE.hat [ARGS...]" >> exitWith (ExitFailure 2)

splitHatFile :: FilePath -> IO (String, String)
splitHatFile path = do
  src <- readFile path
  case lines src of
    [] -> fail "empty .hat file"
    first:rest -> pure (first, unlines rest)

checkHatFile :: FilePath -> IO Bool
checkHatFile path = do
  (first, body) <- splitHatFile path
  case parseHashLine first of
    Nothing -> pure False
    Just declared -> pure (declared == fingerprintText body)

readHatFile :: FilePath -> IO HatFile
readHatFile path = do
  (first, body) <- splitHatFile path
  declared <- maybe (fail "missing first-line hat hash") pure (parseHashLine first)
  let actual = fingerprintText body
  unless (declared == actual) (fail ("hat hash mismatch: declared=" ++ declared ++ " actual=" ++ actual))
  cmds <- parseHatBody body
  pure HatFile { hatPath = path, hatDeclaredHash = declared, hatCommands = cmds }

parseHashLine :: String -> Maybe String
parseHashLine line =
  firstJust
    [ stripPrefixSimple "# hat-hash:" raw
    , stripPrefixSimple "# hat-sha256:" raw
    , stripPrefixSimple "rem hat-hash:" low
    , stripPrefixSimple "rem hat-sha256:" low
    , stripPrefixSimple ":: hat-hash:" low
    , stripPrefixSimple ":: hat-sha256:" low
    ]
  where
    raw = trim line
    low = map toLower raw

firstJust :: [Maybe String] -> Maybe String
firstJust [] = Nothing
firstJust (Nothing:xs) = firstJust xs
firstJust (Just x:_) = Just (trim x)

stripPrefixSimple :: String -> String -> Maybe String
stripPrefixSimple p s
  | p `isPrefixOf` s = Just (drop (length p) s)
  | otherwise = Nothing

fingerprintText :: String -> String
fingerprintText = pad16 . foldl step offset
  where
    offset = 14695981039346656037 :: Integer
    prime = 1099511628211 :: Integer
    mask = 18446744073709551615 :: Integer
    step h c = ((h `xor` toInteger (ord c)) * prime) .&. mask
    pad16 n = let h = showHex n "" in replicate (max 0 (16 - length h)) '0' ++ h

parseHatBody :: String -> IO [HatCommand]
parseHatBody body = mapM parseLine numbered
  where
    ls = zip [(1 :: Int)..] (lines body)
    numbered = filter (not . skipLine . snd) ls

skipLine :: String -> Bool
skipLine raw =
  let s = trim raw
      l = map toLower s
  in null s || "#" `isPrefixOf` s || "rem " `isPrefixOf` l || "::" `isPrefixOf` l

parseLine :: (Int, String) -> IO HatCommand
parseLine (n, raw) = do
  rejectBatchSyntax n raw
  toks <- either (fail . prefix) pure (lexHatLine raw)
  case toks of
    [] -> fail (prefix "empty command")
    ["cd", "/d", dir] -> pure (HatCd dir)
    ["cd", dir] -> pure (HatCd dir)
    ["mkdir", dir] -> pure (HatMkdir dir)
    "run":prog:args -> pure (HatExec prog args)
    prog:args -> pure (HatExec prog args)
  where
    prefix msg = "hat line " ++ show n ++ ": " ++ msg

rejectBatchSyntax :: Int -> String -> IO ()
rejectBatchSyntax n raw = do
  toks <- either (fail . prefix) pure (lexHatLine raw)
  when (any forbiddenToken toks)
    (fail (prefix "outside Hat's per-line invocation subset"))
  when (any badPercent toks)
    (fail (prefix "unsupported batch percent expansion; only %1..%9 and %* are allowed"))
  case toks of
    [] -> pure ()
    first:_ -> when (map toLower first `elem` forbiddenWords || "@" `isPrefixOf` first || ":" `isPrefixOf` first)
      (fail (prefix "unsupported batch control syntax"))
  where
    prefix msg = "hat line " ++ show n ++ ": " ++ msg
    forbiddenWords = ["@echo", "echo", "set", "setlocal", "endlocal", "if", "for", "goto", "call", "pause", "exit", "shift"]
    forbiddenRaw = ["&&", "||", "|", ">", "<", "2>", "1>"]
    forbiddenToken tok = tok `elem` forbiddenRaw
    badPercent tok = '%' `elem` tok && not (tok == "%*" || validPercentPos tok)
    validPercentPos ('%':xs) = not (null xs) && all isDigit xs
    validPercentPos _ = False

lexHatLine :: String -> Either String [String]
lexHatLine = go [] [] Outside
  where
    unterminated = Left "unterminated quoted string"
    go acc cur mode [] =
      case mode of
        InQuote -> unterminated
        _ -> Right (reverse (finish acc cur))
    go acc cur Outside (c:cs)
      | isSpace c = go (finish acc cur) [] Outside cs
      | c == '"' = go acc cur InQuote cs
      | c == '\\' = case cs of
          [] -> go acc (c:cur) Outside []
          d:ds -> go acc (d:cur) Outside ds
      | otherwise = go acc (c:cur) Outside cs
    go acc cur InQuote (c:cs)
      | c == '"' = go acc cur Outside cs
      | c == '\\' = case cs of
          [] -> go acc (c:cur) InQuote []
          d:ds -> go acc (d:cur) InQuote ds
      | otherwise = go acc (c:cur) InQuote cs
    finish acc [] = acc
    finish acc cur = reverse cur : acc

data LexMode = Outside | InQuote deriving Eq

emitHatFile :: FilePath -> IO FilePath
emitHatFile path = do
  absolute <- makeAbsolute path
  hf <- readHatFile absolute
  let out = backendPath absolute (hatDeclaredHash hf)
      generated = renderGenerated hf
  createDirectoryIfMissing True (takeDirectory out)
  exists <- doesFileExist out
  stale <- if exists then not . hasGeneratedHash (hatDeclaredHash hf) <$> readFile out else pure True
  when stale (writeFile out generated)
  pure out

backendPath :: FilePath -> String -> FilePath
backendPath path h =
  takeDirectory path </> ".hat-cache" </> (takeBaseName path ++ "-" ++ h ++ "-" ++ backendVersion ++ ".hs")

hasGeneratedHash :: String -> String -> Bool
hasGeneratedHash h src =
  let header = take 10 (lines src)
  in ("-- hat-source-hash: " ++ h) `elem` header
     && ("-- hat-backend-version: " ++ backendVersion) `elem` header

renderGenerated :: HatFile -> String
renderGenerated hf = unlines $ header ++ concatMap renderCommand (hatCommands hf) ++ footer
  where
    header =
      [ "#!/usr/bin/env cabal"
      , "{- cabal:"
      , "build-depends: base, directory, filepath, process"
      , "-}"
      , "-- generated-from: " ++ takeFileName (hatPath hf)
      , "-- hat-source-hash: " ++ hatDeclaredHash hf
      , "-- hat-backend-version: " ++ backendVersion
      , "module Main where"
      , "import Data.Char (isDigit)"
      , "import System.Directory (createDirectoryIfMissing, setCurrentDirectory)"
      , "import System.Environment (getArgs)"
      , "import System.Exit (ExitCode(..), exitWith)"
      , "import System.Process (rawSystem)"
      , "main :: IO ()"
      , "main = do"
      , "  hatArgs <- getArgs"
      , "  let root = " ++ show (takeDirectory (hatPath hf))
      , "  setCurrentDirectory root"
      ]
    footer =
      [ "  pure ()"
      , "expand :: [String] -> [String] -> [String]"
      , "expand runtime = concatMap (expandOne runtime)"
      , "expandOne :: [String] -> String -> [String]"
      , "expandOne runtime tok"
      , "  | tok == \"$@\" || tok == \"%*\" = runtime"
      , "  | isPosArg tok = maybe [] (\\x -> [x]) (pickArg runtime tok)"
      , "  | otherwise = [tok]"
      , "isPosArg :: String -> Bool"
      , "isPosArg ('$':xs) = not (null xs) && all isDigit xs"
      , "isPosArg ('%':xs) = not (null xs) && all isDigit xs"
      , "isPosArg _ = False"
      , "pickArg :: [String] -> String -> Maybe String"
      , "pickArg runtime (_:xs) = case reads xs of"
      , "  [(n, \"\")] | n > 0 && n <= length runtime -> Just (runtime !! (n - 1))"
      , "  _ -> Nothing"
      , "pickArg _ _ = Nothing"
      , "runStep :: String -> [String] -> IO ()"
      , "runStep prog args = do"
      , "  code <- rawSystem prog args"
      , "  case code of"
      , "    ExitSuccess -> pure ()"
      , "    ExitFailure n -> exitWith (ExitFailure n)"
      ]

renderCommand :: HatCommand -> [String]
renderCommand cmd =
  case cmd of
    HatCd dir -> ["  case expand hatArgs " ++ show [dir] ++ " of", "    [d] -> setCurrentDirectory d", "    _ -> fail \"hat cd expects one path after expansion\""]
    HatMkdir dir -> ["  case expand hatArgs " ++ show [dir] ++ " of", "    [d] -> createDirectoryIfMissing True d", "    _ -> fail \"hat mkdir expects one path after expansion\""]
    HatExec prog args -> ["  runStep " ++ show prog ++ " (expand hatArgs " ++ show args ++ ")"]

runHatFile :: FilePath -> [String] -> IO ()
runHatFile path extra = do
  out <- emitHatFile path
  let dir = takeDirectory out
      file = takeFileName out
  (_, _, _, ph) <- createProcess (proc "cabal" (["run", file, "--"] ++ extra)) { cwd = Just dir }
  code <- waitForProcess ph
  exitWith code

trim :: String -> String
trim = dropWhile isSpace . reverse . dropWhile isSpace . reverse

isSuffixOfSimple :: String -> String -> Bool
isSuffixOfSimple suffix s = reverse suffix `isPrefixOf` reverse s
