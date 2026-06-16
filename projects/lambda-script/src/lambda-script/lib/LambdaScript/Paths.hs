module LambdaScript.Paths where

import System.Directory
import System.FilePath

resolveExamplesRoot :: IO (Either String FilePath)
resolveExamplesRoot = do
  cwd <- getCurrentDirectory
  let roots = take 12 (iterate (</> "..") cwd)
  found <- search roots
  case found of
    Just path -> return (Right path)
    Nothing -> return (Left "lambda-script examples/ not found from cwd")
  where
    search [] = return Nothing
    search (root : rest) = do
      let direct = root </> "examples"
          nested = root </> "lambda-script" </> "examples"
      directOk <- doesFileExist (direct </> "hello.ls")
      nestedOk <- doesFileExist (nested </> "hello.ls")
      if directOk
        then return (Just direct)
        else if nestedOk
          then return (Just nested)
          else search rest