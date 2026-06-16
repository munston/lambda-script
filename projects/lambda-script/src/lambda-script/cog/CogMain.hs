-- generated-by: gofur codegen 0.1
module Main where

import Data.List
import System.Directory
import System.Exit
import System.FilePath
import System.Process

main :: IO ()
main = do
  root <- findProjectRoot
  project <- getCurrentDirectory
  runCase root project "--list" ([] ++ rootArgument "--list" root) (\s -> "--list" `isInfixOf` s)
  runCase root project "--self-test" ([] ++ rootArgument "--self-test" root) (\s -> "lambda-script compiler self-test pass" `isInfixOf` s)
  runCase root project "--describe" ([] ++ rootArgument "--describe" root) (\s -> "Haskell LambdaScript compiler" `isInfixOf` s)
  runCase root project "parse" ([] ++ rootArgument "parse" root) (\s -> "Program" `isInfixOf` s)
  runCase root project "check" ([] ++ rootArgument "check" root) (\s -> "OK: no diagnostics" `isInfixOf` s)
  runCase root project "emit" ([] ++ rootArgument "emit" root) (\s -> "answer = 42" `isInfixOf` s)
  return ()

findProjectRoot :: IO FilePath
findProjectRoot = do
  current <- getCurrentDirectory
  return (normalise (current </> ".." </> ".." </> ".."))

runCase :: FilePath -> FilePath -> String -> [String] -> (String -> Bool) -> IO ()
runCase _root project option extraArgs predicate = do
  let exe = project </> "bin" </> "lambda-script.exe"
      args = option : extraArgs
  output <- readProcess exe args ""
  let value = read output :: String
  if predicate value
    then return ()
    else do
      putStrLn ("cog failed for " ++ option ++ ": " ++ value)
      exitFailure

rootArgument :: String -> FilePath -> [String]
rootArgument option root
  | option `elem` rootOptions = [root]
  | otherwise = []

rootOptions :: [String]
rootOptions = ["--check","--object-check","--compile-wires","--cast","--halt-project-bin","--clean-project-bin","--cabal-install","--test","--record-verification","--verification-status","--versioning-push","--ship-bin","--make"]
