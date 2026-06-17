#!/usr/bin/env cabal
{- cabal:
build-depends: base, directory, filepath, process
-}
-- generated-from: installation_script.hat
-- hat-source-hash: c48cd949d3b5dbd3
module Main where
import System.Directory (createDirectoryIfMissing, getCurrentDirectory, setCurrentDirectory)
import System.Exit (ExitCode(..), exitWith)
import System.FilePath ((</>))
import System.Process (rawSystem)
main :: IO ()
main = do
  root <- getCurrentDirectory
  let installDir = root </> "bin"
  createDirectoryIfMissing True installDir
  runStep "cabal" ["install", "exe:hat", "--install-method=copy", "--overwrite-policy=always", "--installdir=" ++ installDir]
  pure ()
runStep :: String -> [String] -> IO ()
runStep prog args = do
  code <- rawSystem prog args
  case code of
    ExitSuccess -> pure ()
    ExitFailure n -> exitWith (ExitFailure n)
