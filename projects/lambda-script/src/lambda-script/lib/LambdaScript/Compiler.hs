module LambdaScript.Compiler where

import System.IO

import LambdaScript.Codegen.Haskell
import LambdaScript.Core.Check
import LambdaScript.Core.Diagnostic
import LambdaScript.Core.Program
import LambdaScript.Parser.Parser

data CompileResult = CompileResult
  { compileProgram :: Maybe Program
  , compileDiagnostics :: [Diagnostic]
  , compileHaskell :: Maybe String
  } deriving (Eq, Show, Read)

readSourceFile :: FilePath -> IO String
readSourceFile path = readFile path

parseSource :: String -> FilePath -> CompileResult
parseSource source path =
  let result = parse source path
  in CompileResult
       { compileProgram = parseProgram result
       , compileDiagnostics = parseDiagnostics result
       , compileHaskell = Nothing
       }

checkParsed :: Program -> CompileResult
checkParsed program =
  let diags = checkProgram program
  in CompileResult
       { compileProgram = if null diags then Just program else Nothing
       , compileDiagnostics = diags
       , compileHaskell = Nothing
       }

emitHaskellProgram :: Program -> CompileResult
emitHaskellProgram program =
  CompileResult
    { compileProgram = Just program
    , compileDiagnostics = []
    , compileHaskell = Just (emitHaskell program)
    }

compileFileToHaskell :: FilePath -> IO CompileResult
compileFileToHaskell path = do
  source <- readSourceFile path
  let parsed = parseSource source path
  case compileProgram parsed of
    Nothing -> return parsed
    Just program ->
      let checked = checkParsed program
      in case compileProgram checked of
        Nothing -> return checked
        Just ok -> return (emitHaskellProgram ok)

formatDiagnostics :: [Diagnostic] -> String
formatDiagnostics diags = unlines (map diagnosticLine diags)