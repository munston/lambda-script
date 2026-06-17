#!/usr/bin/env cabal
{- cabal:
build-depends: base, directory, filepath, process
-}

module Main where

import System.Directory (createDirectoryIfMissing, getCurrentDirectory)
import System.Exit (ExitCode(..), exitWith)
import System.FilePath ((</>))
import System.Process (rawSystem)

main :: IO ()
main = do
  root <- getCurrentDirectory
  let binDir = root </> "bin"
  createDirectoryIfMissing True binDir
  code <- rawSystem "cabal"
    [ "install"
    , "exe:hat"
    , "--install-method=copy"
    , "--overwrite-policy=always"
    , "--installdir=" ++ binDir
    ]
  case code of
    ExitSuccess -> putStrLn ("hat installed to " ++ binDir) >> pure ()
    ExitFailure n -> exitWith (ExitFailure n)
