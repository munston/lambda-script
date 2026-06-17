module Hat
  ( message
  , mainHat
  , fingerprintText
  , checkHatFile
  , emitHatFile
  ) where

import Control.Monad (unless, when)
import Data.Bits (xor, (.&.))
import Data.Char (isSpace, ord)
import Data.List (isPrefixOf)
import Numeric (showHex)
import System.Directory (doesFileExist)
import System.Environment (getArgs)
import System.Exit (ExitCode(..), exitWith)
import System.FilePath (replaceExtension, takeDirectory, takeFileName)
import System.IO (hPutStrLn, stderr)
import System.Process (CreateProcess(..), proc, waitForProcess, createProcess)

message :: String
message = "hat!"

data HatFile = HatFile
  { hatPath :: FilePath
  , hatDeclaredHash :: String
  , hatBody :: String
  , hatCommands :: [HatCommand]
  } deriving (Eq, Show)

data HatCommand
  = HatSay String
  | HatCd FilePath
  | HatMkdir FilePath
  | HatRun String [String]
  | HatInstallCopy String FilePath
  deriving (Eq, Show)

mainHat :: IO ()
mainHat = do
  args <- getArgs
  case args of
    [] -> putStrLn message
    ["help"] -> usage
    ["hash", file] -> fingerprintText . snd <$> splitHatFile file >>= putStrLn
    ["check", file] -> checkHatFile file >>= printCheck
    ["emit", file] -> emitHatFile file >>= putStrLn
    ["run", file] -> runHatFile file []
    "run":file:"--":rest -> runHatFile file rest
    "run":file:rest -> runHatFile file rest
    ["stamp", file] -> stampHatFile file
    _ -> hPutStrLn stderr "hat: invalid arguments" >> usage >> exitWith (ExitFailure 2)

usage :: IO ()
usage = do
  putStrLn "hat commands:"
  putStrLn "  hat"
  putStrLn "  hat help"
  putStrLn "  hat hash FILE.hat"
  putStrLn "  hat check FILE.hat"
  putStrLn "  hat stamp FILE.hat"
  putStrLn "  hat emit FILE.hat"
  putStrLn "  hat run FILE.hat [-- ARGS...]"

printCheck :: Bool -> IO ()
printCheck ok = putStrLn (if ok then "hat: fingerprint ok" else "hat: fingerprint mismatch") >> unless ok (exitWith (ExitFailure 1))

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
  pure HatFile { hatPath = path, hatDeclaredHash = declared, hatBody = body, hatCommands = cmds }

parseHashLine :: String -> Maybe String
parseHashLine line =
  case stripPrefix "# hat-hash:" line of
    Just rest -> Just (trim rest)
    Nothing -> case stripPrefix "# hat-sha256:" line of
      Just rest -> Just (trim rest)
      Nothing -> Nothing

stripPrefix :: String -> String -> Maybe String
stripPrefix p s
  | p `isPrefixOf` s = Just (drop (length p) s)
  | otherwise = Nothing

stampHatFile :: FilePath -> IO ()
stampHatFile path = do
  (_, body) <- splitHatFile path
  writeFile path ("# hat-hash: " ++ fingerprintText body ++ "\n" ++ body)
  putStrLn ("hat: stamped " ++ path)

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
    meaningful = filter (not . null . trim . snd) (zip [(1 :: Int)..] (lines body))
    numbered = filter (not . isPrefixOf "#" . trim . snd) meaningful

parseLine :: (Int, String) -> IO HatCommand
parseLine (n, raw) =
  case words raw of
    ["hat", _] -> pure (HatSay "")
    "say":xs -> pure (HatSay (unwords xs))
    ["cd", dir] -> pure (HatCd dir)
    ["mkdir", dir] -> pure (HatMkdir dir)
    "run":prog:args -> pure (HatRun prog args)
    ["install-copy", exe, dir] -> pure (HatInstallCopy exe dir)
    _ -> fail ("unsupported hat command at line " ++ show n ++ ": " ++ raw)

emitHatFile :: FilePath -> IO FilePath
emitHatFile path = do
  hf <- readHatFile path
  let out = replaceExtension path "hs"
      generated = renderGenerated hf
  exists <- doesFileExist out
  stale <- if exists then not . hasGeneratedHash (hatDeclaredHash hf) <$> readFile out else pure True
  when stale (writeFile out generated)
  pure out

hasGeneratedHash :: String -> String -> Bool
hasGeneratedHash h src = ("-- hat-source-hash: " ++ h) `elem` take 8 (lines src)

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
      , "module Main where"
      , "import System.Directory (createDirectoryIfMissing, getCurrentDirectory, setCurrentDirectory)"
      , "import System.Exit (ExitCode(..), exitWith)"
      , "import System.FilePath ((</>))"
      , "import System.Process (rawSystem)"
      , "main :: IO ()"
      , "main = do"
      , "  root <- getCurrentDirectory"
      ]
    footer =
      [ "  pure ()"
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
    HatSay "" -> []
    HatSay msg -> ["  putStrLn " ++ show msg]
    HatCd dir -> ["  setCurrentDirectory " ++ show dir]
    HatMkdir dir -> ["  createDirectoryIfMissing True " ++ show dir]
    HatRun prog args -> ["  runStep " ++ show prog ++ " " ++ show args]
    HatInstallCopy exe dir ->
      [ "  let installDir = root </> " ++ show dir
      , "  createDirectoryIfMissing True installDir"
      , "  runStep \"cabal\" [\"install\", \"exe:" ++ exe ++ "\", \"--install-method=copy\", \"--overwrite-policy=always\", \"--installdir=\" ++ installDir]"
      ]

runHatFile :: FilePath -> [String] -> IO ()
runHatFile path extra = do
  out <- emitHatFile path
  let dir = takeDirectory out
      file = takeFileName out
  (_, _, _, ph) <- createProcess (proc "cabal" (["run", file] ++ extra)) { cwd = Just dir }
  code <- waitForProcess ph
  exitWith code

trim :: String -> String
trim = dropWhile isSpace . reverse . dropWhile isSpace . reverse
