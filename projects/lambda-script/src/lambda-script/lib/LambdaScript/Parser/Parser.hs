module LambdaScript.Parser.Parser where

import Control.Applicative
import Data.Char
import Data.List
import Data.Maybe
import qualified Data.Map.Strict as Map

import LambdaScript.Core.Ast
import LambdaScript.Core.Diagnostic
import LambdaScript.Core.Program

data ParseResult = ParseResult
  { parseProgram :: Maybe Program
  , parseDiagnostics :: [Diagnostic]
  } deriving (Eq, Show, Read)

validFfiTypes :: [String]
validFfiTypes = ["i32", "f64", "bool", "string", "void"]

binaryPrecedence :: [[String]]
binaryPrecedence =
  [ ["==", "!=", "<=", ">=", "<", ">"]
  , ["+", "-"]
  , ["*", "/"]
  ]

data Acc = Acc
  { accCurrent :: Maybe Module
  , accPending :: Map.Map String FunctionSignature
  , accModules :: [Module]
  , accDiags :: [Diagnostic]
  }

parse :: String -> String -> ParseResult
parse source filename =
  let rows = zip [1 ..] (lines source)
      final = foldl (stepLine filename) (Acc Nothing Map.empty [] []) rows
      closed = closeModule final
  in ParseResult
       { parseProgram =
           if null (accDiags closed)
             then Just (Program (reverse (accModules closed)))
             else Nothing
       , parseDiagnostics = accDiags closed
       }

closeModule :: Acc -> Acc
closeModule acc =
  case accCurrent acc of
    Nothing -> acc
    Just mod ->
      acc
        { accModules = mod : accModules acc
        , accCurrent = Nothing
        , accPending = Map.empty
        , accDiags = accDiags acc ++ danglingDiags (moduleName mod) (accPending acc)
        }

stepLine :: String -> Acc -> (Int, String) -> Acc
stepLine filename acc (lineNo, rawLine) =
  let line = trim rawLine
  in if null line || "//" `isPrefixOf` line
       then acc
       else case parseModuleHeader line of
         Just name ->
           let closed = closeModule acc
           in closed { accCurrent = Just (Module name []), accPending = Map.empty }
         Nothing ->
           case accCurrent acc of
             Nothing -> acc { accDiags = accDiags acc ++ [Diagnostic ("No active module at line " ++ show lineNo)] }
             Just mod -> handleDecl filename lineNo line acc mod

handleDecl :: String -> Int -> String -> Acc -> Module -> Acc
handleDecl filename lineNo line acc mod =
  case parseTypeSignatureLine line of
    Just (sigName, sigText) ->
      case parseSignatureText sigText of
        Nothing -> acc { accDiags = accDiags acc ++ [Diagnostic ("Invalid type signature at line " ++ show lineNo)] }
        Just sig ->
          if Map.member sigName (accPending acc)
            then acc { accDiags = accDiags acc ++ [Diagnostic ("Duplicate type signature for " ++ sigName ++ " at line " ++ show lineNo)] }
            else acc { accPending = Map.insert sigName sig (accPending acc) }
    Nothing ->
      case parseForeignLine line of
        Just foreignDecl ->
          acc { accCurrent = Just (mod { moduleDeclarations = moduleDeclarations mod ++ [TopForeign foreignDecl] }) }
        Nothing ->
          case parseFunctionLine filename lineNo line (accPending acc) of
            Right (fn, pending') ->
              acc
                { accCurrent = Just (mod { moduleDeclarations = moduleDeclarations mod ++ [TopFunction fn] })
                , accPending = pending'
                }
            Left _ ->
              case parseDeclarationLine filename lineNo line of
                Nothing -> acc { accDiags = accDiags acc ++ [Diagnostic ("Invalid line at " ++ show lineNo ++ ": " ++ line)] }
                Just decl ->
                  acc { accCurrent = Just (mod { moduleDeclarations = moduleDeclarations mod ++ [TopDeclaration decl] }) }

danglingDiags :: String -> Map.Map String FunctionSignature -> [Diagnostic]
danglingDiags modName pending =
  [ Diagnostic ("Dangling type signature for " ++ name ++ " in module " ++ modName) | name <- Map.keys pending ]

parseModuleHeader :: String -> Maybe String
parseModuleHeader line =
  case words line of
    ["module", name] | isIdent name -> Just name
    _ -> Nothing

parseTypeSignatureLine :: String -> Maybe (String, String)
parseTypeSignatureLine line =
  case words line of
    _ | "foreign" `isPrefixOf` line -> Nothing
    _ | functionShape line -> Nothing
    _ ->
      case break (== ':') line of
        (left, ':' : rest) ->
          let name = trim left
              sigText = trim rest
          in if isIdent name && "->" `isInfixOf` sigText then Just (name, sigText) else Nothing
        _ -> Nothing

functionShape :: String -> Bool
functionShape line =
  case elemIndex '=' line of
    Nothing -> False
    Just eqIdx ->
      let left = trim (take eqIdx line)
      in length (words left) > 1

parseForeignLine :: String -> Maybe ForeignImport
parseForeignLine line =
  let trimmed = trim line
  in if "foreign cpp " `isPrefixOf` trimmed && " = \"" `isInfixOf` trimmed
       then
         let withoutPrefix = drop (length "foreign cpp ") trimmed
             (namePart, rest1) = break (== ':') withoutPrefix
             name = trim namePart
             sigText = trim (takeWhile (/= '=') (drop 1 rest1))
             afterEq = dropWhile (/= '"') (drop 1 rest1)
             symbol = takeWhile (/= '"') (drop 1 afterEq)
         in if isIdent name
              then case parseSignatureText sigText of
                Nothing -> Nothing
                Just sig ->
                  Just
                    ForeignImport
                      { foreignTarget = ForeignCpp
                      , foreignName = Identifier name Nothing
                      , foreignSymbol = symbol
                      , foreignSignature = ForeignSignature (functionParams sig) (functionResult sig)
                      , foreignSpan = Nothing
                      }
              else Nothing
       else Nothing

parseFunctionLine :: String -> Int -> String -> Map.Map String FunctionSignature -> Either String (FunctionDeclaration, Map.Map String FunctionSignature)
parseFunctionLine filename lineNo line pending =
  case elemIndex '=' line of
    Nothing -> Left "not a function"
    Just eqIdx ->
      let left = trim (take eqIdx line)
          right = trim (drop (eqIdx + 1) line)
          parts = words left
      in case parts of
        [name] -> Left "not a function"
        name : paramNames ->
          case Map.lookup name pending of
            Nothing -> Left ("Missing type signature for function " ++ name ++ " at line " ++ show lineNo)
            Just sig ->
              if length paramNames /= length (functionParams sig)
                then Left ("Parameter count does not match signature for " ++ name ++ " at line " ++ show lineNo)
                else
                  let span = Span filename (lineNo - 1) (lineNo - 1)
                      params = map (\p -> Identifier p (Just span)) paramNames
                  in case parseExpression right span of
                    Nothing -> Left ("Invalid function body at line " ++ show lineNo)
                    Just body ->
                      Right
                        ( FunctionDeclaration
                            { functionName = Identifier name (Just span)
                            , functionBoundParams = params
                            , functionSignature = sig
                            , functionBody = body
                            , functionSpan = Just span
                            }
                        , Map.delete name pending
                        )

parseDeclarationLine :: String -> Int -> String -> Maybe Declaration
parseDeclarationLine filename lineNo line =
  case break (== '=') line of
    (left, '=' : rest) ->
      let name = trim left
          valueText = trim rest
          span = Span filename (lineNo - 1) (lineNo - 1)
      in if isIdent name && length (words left) == 1
           then case parseExpression valueText span of
             Nothing -> Nothing
             Just value ->
               Just
                 Declaration
                   { declarationName = Identifier name (Just span)
                   , declarationValue = value
                   , declarationSpan = Just span
                   }
           else Nothing
    _ -> Nothing

parseSignatureText :: String -> Maybe FunctionSignature
parseSignatureText text =
  let parts = map trim (splitOnArrow text)
  in if length parts < 2
       then Nothing
       else
         let resultType = last parts
             paramTypes = init parts
         in if all isValidFfiType (resultType : paramTypes) && not (elem "void" paramTypes)
              then
                Just
                  FunctionSignature
                    { functionParams = map parseFfiType paramTypes
                    , functionResult = parseFfiType resultType
                    }
              else Nothing

splitOnArrow :: String -> [String]
splitOnArrow text =
  case breakSubstring "->" text of
    Nothing -> [trim text]
    Just (before, after) -> trim before : splitOnArrow after

breakSubstring :: String -> String -> Maybe (String, String)
breakSubstring needle hay =
  case findSubstring needle hay of
    Nothing -> Nothing
    Just idx -> Just (take idx hay, drop (idx + length needle) hay)

findSubstring :: String -> String -> Maybe Int
findSubstring needle hay = go 0
  where
    go i
      | i > length hay - length needle = Nothing
      | take (length needle) (drop i hay) == needle = Just i
      | otherwise = go (i + 1)

isValidFfiType :: String -> Bool
isValidFfiType t = t `elem` validFfiTypes

parseFfiType :: String -> ForeignPrimitiveType
parseFfiType t = case t of
  "i32" -> TyI32
  "f64" -> TyF64
  "bool" -> TyBool
  "string" -> TyString
  _ -> TyVoid

parseExpression :: String -> Span -> Maybe Expression
parseExpression text span =
  let s = stripOuterParens (trim text)
  in parseLet s span
     <|> parseIf s span
     <|> parseBinary s span
     <|> parseLiteral s span
     <|> parseCall s span
     <|> parseIdent s span

parseLet :: String -> Span -> Maybe Expression
parseLet s span =
  if "let " `isPrefixOf` s
    then case findKeywordAtTopLevel s "in" of
      Nothing -> Nothing
      Just inIdx ->
        let binding = trim (drop 4 (take inIdx s))
            bodyText = trim (drop (inIdx + 2) s)
        in case findBindingEqualsAtTopLevel binding of
          Nothing -> Nothing
          Just eqIdx ->
            let nameText = trim (take eqIdx binding)
                valueText = trim (drop (eqIdx + 1) binding)
            in if isIdent nameText
                 then do
                   value <- parseExpression valueText span
                   body <- parseExpression bodyText span
                   return
                     ( ExprLet
                         LetExpression
                           { letName = Identifier nameText (Just span)
                           , letValue = value
                           , letBody = body
                           , letSpan = Just span
                           }
                     )
                 else Nothing
    else Nothing

parseIf :: String -> Span -> Maybe Expression
parseIf s span =
  if "if " `isPrefixOf` s
    then case findKeywordAtTopLevel s "then" of
      Nothing -> Nothing
      Just thenIdx ->
        let afterThen = drop (thenIdx + 4) s
        in case findKeywordAtTopLevel afterThen "else" of
          Nothing -> Nothing
          Just elseIdx ->
            let condText = trim (drop 3 (take thenIdx s))
                thenText = trim (take elseIdx afterThen)
                elseText = trim (drop (elseIdx + 4) afterThen)
            in do
              condition <- parseExpression condText span
              thenBranch <- parseExpression thenText span
              elseBranch <- parseExpression elseText span
              return
                ( ExprIf
                    IfExpression
                      { ifCondition = condition
                      , ifThenBranch = thenBranch
                      , ifElseBranch = elseBranch
                      , ifSpan = Just span
                      }
                )
    else Nothing

parseBinary :: String -> Span -> Maybe Expression
parseBinary s span = foldr (\ops acc -> acc <|> tryOpGroup ops s span) Nothing binaryPrecedence

tryOpGroup :: [String] -> String -> Span -> Maybe Expression
tryOpGroup ops s span =
  case findOperatorAtTopLevel s ops of
    Nothing -> Nothing
    Just (idx, op) ->
      let leftText = trim (take idx s)
          rightText = trim (drop (idx + length op) s)
      in do
        left <- parseExpression leftText span
        right <- parseExpression rightText span
        return
          ( ExprBinary
              BinaryExpression
                { binaryOperator = op
                , binaryLeft = left
                , binaryRight = right
                , binarySpan = Just span
                }
          )

parseLiteral :: String -> Span -> Maybe Expression
parseLiteral s span
  | s == "true" = Just (ExprLiteral Literal { literalValue = LitBool True, literalSpan = Just span })
  | s == "false" = Just (ExprLiteral Literal { literalValue = LitBool False, literalSpan = Just span })
  | length s >= 2 && head s == '"' && last s == '"' =
      Just (ExprLiteral Literal { literalValue = LitString (init (tail s)), literalSpan = Just span })
  | otherwise =
      case reads s :: [(Integer, String)] of
        [(n, "")] -> Just (ExprLiteral Literal { literalValue = LitInt n, literalSpan = Just span })
        _ ->
          case reads s :: [(Double, String)] of
            [(n, "")] -> Just (ExprLiteral Literal { literalValue = LitDouble n, literalSpan = Just span })
            _ -> Nothing

parseCall :: String -> Span -> Maybe Expression
parseCall s span =
  case break (== '(') s of
    (namePart, '(' : rest) ->
      let name = trim namePart
          inner = case reverse rest of
            ')' : xs -> reverse xs
            _ -> rest
      in if isIdent name
           then
             let argTexts = if null (trim inner) then [] else splitArgs inner
                 parsed = map (\a -> parseExpression a span) argTexts
             in if all isJust parsed
                  then
                    Just
                      ( ExprCall
                          CallExpression
                            { callCallee = Identifier name (Just span)
                            , callArguments = map fromJust parsed
                            , callSpan = Just span
                            }
                      )
                  else Nothing
           else Nothing
    _ -> Nothing

parseIdent :: String -> Span -> Maybe Expression
parseIdent s span =
  if isIdent s then Just (ExprIdentifier (Identifier s (Just span))) else Nothing

stripOuterParens :: String -> String
stripOuterParens s = stripOuterParensLoop (trim s)

stripOuterParensLoop :: String -> String
stripOuterParensLoop s =
  if length s >= 2 && head s == '(' && last s == ')'
    then
      let inner = init (tail s)
          depths = scanl (\d c -> d + parenDelta c) 0 inner
      in if not (null depths) && last depths == 0 && all (>= 0) depths
           then stripOuterParensLoop (trim inner)
           else s
    else s

parenDelta :: Char -> Int
parenDelta '(' = 1
parenDelta ')' = -1
parenDelta _ = 0

findKeywordAtTopLevel :: String -> String -> Maybe Int
findKeywordAtTopLevel text keyword = go 0 False 0
  where
    go i inString depth
      | i > length text - length keyword = Nothing
      | otherwise =
          let ch = text !! i
              inString' = if ch == '"' then not inString else inString
              depth' =
                if inString'
                  then depth
                  else case ch of
                    '(' -> depth + 1
                    ')' -> depth - 1
                    _ -> depth
          in if not inString' && depth == 0 && take (length keyword) (drop i text) == keyword
               then
                 let before = if i == 0 then ' ' else text !! (i - 1)
                     afterIdx = i + length keyword
                     after = if afterIdx >= length text then ' ' else text !! afterIdx
                 in if isSpace before && isSpace after then Just i else go (i + 1) inString' depth'
               else go (i + 1) inString' depth'

findBindingEqualsAtTopLevel :: String -> Maybe Int
findBindingEqualsAtTopLevel text = go 0 False 0
  where
    go i inString depth
      | i >= length text = Nothing
      | otherwise =
          let ch = text !! i
              inString' = if ch == '"' then not inString else inString
              depth' =
                if inString'
                  then depth
                  else case ch of
                    '(' -> depth + 1
                    ')' -> depth - 1
                    _ -> depth
          in if not inString' && depth == 0 && ch == '='
               then
                 let prev = if i > 0 then text !! (i - 1) else ' '
                     next = if i + 1 < length text then text !! (i + 1) else ' '
                 in if prev `elem` "<>!=" || next == '=' then go (i + 1) inString' depth' else Just i
               else go (i + 1) inString' depth'

findOperatorAtTopLevel :: String -> [String] -> Maybe (Int, String)
findOperatorAtTopLevel text ops = go (length text - 1) False 0
  where
    go i inString depth
      | i < 0 = Nothing
      | otherwise =
          let ch = text !! i
              inString' = if ch == '"' then not inString else inString
              depth' =
                if inString'
                  then depth
                  else case ch of
                    ')' -> depth + 1
                    '(' -> depth - 1
                    _ -> depth
          in if not inString' && depth == 0
               then case tryOpsAt text ops i of
                 Just found -> Just found
                 Nothing -> go (i - 1) inString' depth'
               else go (i - 1) inString' depth'

tryOpsAt :: String -> [String] -> Int -> Maybe (Int, String)
tryOpsAt text ops i = foldr (\op acc -> acc <|> tryOne text i op) Nothing ops

tryOne :: String -> Int -> String -> Maybe (Int, String)
tryOne text i op =
  let start = i - length op + 1
  in if start < 0
       then Nothing
       else
         if take (length op) (drop start text) == op
           then
             let prev = if start > 0 then text !! (start - 1) else ' '
             in if (op == "-" || op == "+") && (start == 0 || prev `elem` "+-*/<>=!(")
                  then Nothing
                  else Just (start, op)
           else Nothing

splitArgs :: String -> [String]
splitArgs text = go 0 False 0 0
  where
    go i inString depth start =
      if i >= length text
        then let lastPart = trim (drop start text) in if null lastPart then [] else [lastPart]
        else
          let ch = text !! i
              inString' = if ch == '"' then not inString else inString
              depth' =
                if inString'
                  then depth
                  else case ch of
                    '(' -> depth + 1
                    ')' -> depth - 1
                    _ -> depth
          in if not inString' && ch == ',' && depth == 0
               then trim (take (i - start) (drop start text)) : go (i + 1) inString' depth' (i + 1)
               else go (i + 1) inString' depth' start

trim :: String -> String
trim = reverse . dropWhile isSpace . reverse . dropWhile isSpace

isIdent :: String -> Bool
isIdent s =
  case s of
    [] -> False
    c : cs -> isAlpha c && all (\x -> isAlphaNum x || x == '_') cs