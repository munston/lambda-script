-- | Content hashing + canonical JSON (ported from forks.py sha256_text /
-- replay_ledger.canonical_json / json_sha256). Canonical JSON mirrors Python's
-- json.dumps(sort_keys=True, separators=(",", ":")) so digests are stable.
module LambdaScript.Forks.Hash
  ( sha256Text
  , canonicalJson
  , jsonSha256
  ) where

import Data.Aeson (Value(..))
import qualified Data.Aeson.Key as K
import qualified Data.Aeson.KeyMap as KM
import Data.Digest.Pure.SHA (sha256, showDigest)
import Data.Foldable (toList)
import Data.List (intercalate, sortOn)
import qualified Data.Scientific as Sci
import qualified Data.Text as T
import qualified Data.Text.Lazy as TL
import qualified Data.Text.Lazy.Encoding as TLE

-- | SHA-256 hex digest of a UTF-8 string.
sha256Text :: String -> String
sha256Text = showDigest . sha256 . TLE.encodeUtf8 . TL.pack

-- | SHA-256 of the canonical JSON encoding of a value.
jsonSha256 :: Value -> String
jsonSha256 = sha256Text . canonicalJson

-- | Deterministic JSON: object keys sorted, compact separators.
canonicalJson :: Value -> String
canonicalJson val =
  case val of
    Object o ->
      let pairs = sortOn fst [ (K.toString k, v) | (k, v) <- KM.toList o ]
      in "{" ++ intercalate "," [ encStr k ++ ":" ++ canonicalJson v | (k, v) <- pairs ] ++ "}"
    Array a -> "[" ++ intercalate "," (map canonicalJson (toList a)) ++ "]"
    String s -> encStr (T.unpack s)
    Number n ->
      case (Sci.floatingOrInteger n :: Either Double Integer) of
        Left d -> show d
        Right i -> show i
    Bool b -> if b then "true" else "false"
    Null -> "null"

encStr :: String -> String
encStr s = "\"" ++ concatMap esc s ++ "\""
  where
    esc c = case c of
      '"' -> "\\\""
      '\\' -> "\\\\"
      '\n' -> "\\n"
      '\r' -> "\\r"
      '\t' -> "\\t"
      _ -> [c]
