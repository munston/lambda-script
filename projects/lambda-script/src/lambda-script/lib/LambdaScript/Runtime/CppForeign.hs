module LambdaScript.Runtime.CppForeign where

import Data.List (isInfixOf)
import System.Exit (ExitCode (ExitFailure, ExitSuccess))
import System.Process (readProcessWithExitCode)

data CppForeignValue
  = CppNumber Double
  | CppBool Bool
  | CppString String
  | CppNull
  deriving (Eq, Show, Read)

data CppForeignRequest = CppForeignRequest
  { cppForeignSymbol :: String
  , cppForeignArgs :: [CppForeignValue]
  } deriving (Eq, Show, Read)

data CppForeignRuntime = CppForeignRuntime
  { cppForeignCall :: CppForeignRequest -> IO CppForeignValue
  }

data CppProcessRuntime = CppProcessRuntime
  { cppProcessExecutable :: FilePath
  } deriving (Eq, Show, Read)

newCppProcessRuntime :: FilePath -> CppForeignRuntime
newCppProcessRuntime executable =
  CppForeignRuntime
    { cppForeignCall = callCppProcess executable
    }

callCppProcess :: FilePath -> CppForeignRequest -> IO CppForeignValue
callCppProcess executable request = do
  (exitCode, stdoutText, stderrText) <-
    readProcessWithExitCode executable [encodeRequest request] ""
  case exitCode of
    ExitFailure _ ->
      fail (if null stderrText then "FFI call failed" else stderrText)
    ExitSuccess ->
      case decodeResponse stdoutText of
        Left err -> fail err
        Right value -> pure value

encodeRequest :: CppForeignRequest -> String
encodeRequest request =
  "{\"symbol\":"
    ++ encodeString (cppForeignSymbol request)
    ++ ",\"args\":["
    ++ intercalateValues (map encodeValue (cppForeignArgs request))
    ++ "]}"

encodeValue :: CppForeignValue -> String
encodeValue value = case value of
  CppNumber n -> show n
  CppBool True -> "true"
  CppBool False -> "false"
  CppString s -> encodeString s
  CppNull -> "null"

encodeString :: String -> String
encodeString s = "\"" ++ concatMap escapeChar s ++ "\""

escapeChar :: Char -> String
escapeChar c = case c of
  '"' -> "\\\""
  '\\' -> "\\\\"
  '\n' -> "\\n"
  '\r' -> "\\r"
  '\t' -> "\\t"
  _ -> [c]

intercalateValues :: [String] -> String
intercalateValues [] = ""
intercalateValues (x : xs) = x ++ concatMap (',' :) xs

decodeResponse :: String -> Either String CppForeignValue
decodeResponse raw =
  let trimmed = dropWhile (== ' ') raw
  in if not (startsWith "{\"ok\":" trimmed)
       then Left "FFI error"
       else
         if "\"ok\":false" `isInfixOf` trimmed
           then Left (extractError trimmed)
           else case extractField "value" trimmed of
             Nothing -> Left "FFI error"
             Just valueText -> decodeValue valueText

extractError :: String -> String
extractError raw =
  case extractField "error" raw of
    Nothing -> "FFI error"
    Just err -> err

extractField :: String -> String -> Maybe String
extractField key raw =
  let needle = "\"" ++ key ++ "\":"
  in case dropPrefix needle raw of
    Nothing -> Nothing
    Just rest ->
      let trimmed = dropWhile (== ' ') rest
      in if null trimmed
           then Nothing
           else if head trimmed == '"'
                then Just (readJsonString (tail trimmed))
                else Just (takeWhile (\c -> c /= ',' && c /= '}') trimmed)

dropPrefix :: String -> String -> Maybe String
dropPrefix prefix raw =
  if take (length prefix) raw == prefix
    then Just (drop (length prefix) raw)
    else Nothing

startsWith :: String -> String -> Bool
startsWith prefix raw = take (length prefix) raw == prefix

readJsonString :: String -> String
readJsonString = go []
  where
    go acc (c : cs) = case c of
      '"' -> reverse acc
      '\\' -> case cs of
        '\\' : rest -> go ('\\' : acc) rest
        '"' : rest -> go ('"' : acc) rest
        'n' : rest -> go ('\n' : acc) rest
        'r' : rest -> go ('\r' : acc) rest
        't' : rest -> go ('\t' : acc) rest
        _ : rest -> go acc rest
        [] -> reverse acc
      _ -> go (c : acc) cs
    go acc [] = reverse acc

decodeValue :: String -> Either String CppForeignValue
decodeValue raw =
  let trimmed = dropWhile (== ' ') raw
  in if trimmed == "null"
       then Right CppNull
       else if trimmed == "true"
            then Right (CppBool True)
            else if trimmed == "false"
                 then Right (CppBool False)
                 else if not (null trimmed) && head trimmed == '"'
                      then Right (CppString (readJsonString (tail trimmed)))
                      else case reads trimmed :: [(Double, String)] of
                        [(n, _)] -> Right (CppNumber n)
                        _ -> Left "FFI error"

