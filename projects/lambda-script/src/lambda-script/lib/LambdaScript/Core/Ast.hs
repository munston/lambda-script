module LambdaScript.Core.Ast where

data Span = Span
  { spanFile :: String
  , spanStart :: Int
  , spanEnd :: Int
  } deriving (Eq, Show, Read)

data Identifier = Identifier
  { identifierName :: String
  , identifierSpan :: Maybe Span
  } deriving (Eq, Show, Read)

data LiteralValue
  = LitString String
  | LitInt Integer
  | LitDouble Double
  | LitBool Bool
  deriving (Eq, Show, Read)

data Literal = Literal
  { literalValue :: LiteralValue
  , literalSpan :: Maybe Span
  } deriving (Eq, Show, Read)

data Expression
  = ExprIdentifier Identifier
  | ExprLiteral Literal
  | ExprCall CallExpression
  | ExprBinary BinaryExpression
  | ExprIf IfExpression
  | ExprLet LetExpression
  deriving (Eq, Show, Read)

data CallExpression = CallExpression
  { callCallee :: Identifier
  , callArguments :: [Expression]
  , callSpan :: Maybe Span
  } deriving (Eq, Show, Read)

data BinaryExpression = BinaryExpression
  { binaryOperator :: String
  , binaryLeft :: Expression
  , binaryRight :: Expression
  , binarySpan :: Maybe Span
  } deriving (Eq, Show, Read)

data IfExpression = IfExpression
  { ifCondition :: Expression
  , ifThenBranch :: Expression
  , ifElseBranch :: Expression
  , ifSpan :: Maybe Span
  } deriving (Eq, Show, Read)

data LetExpression = LetExpression
  { letName :: Identifier
  , letValue :: Expression
  , letBody :: Expression
  , letSpan :: Maybe Span
  } deriving (Eq, Show, Read)

data ForeignTarget = ForeignCpp
  deriving (Eq, Show, Read)

data ForeignPrimitiveType
  = TyI32
  | TyF64
  | TyBool
  | TyString
  | TyVoid
  deriving (Eq, Show, Read)

data ForeignSignature = ForeignSignature
  { foreignParams :: [ForeignPrimitiveType]
  , foreignResult :: ForeignPrimitiveType
  } deriving (Eq, Show, Read)

data FunctionSignature = FunctionSignature
  { functionParams :: [ForeignPrimitiveType]
  , functionResult :: ForeignPrimitiveType
  } deriving (Eq, Show, Read)

data TopLevel
  = TopDeclaration Declaration
  | TopFunction FunctionDeclaration
  | TopForeign ForeignImport
  deriving (Eq, Show, Read)

data Declaration = Declaration
  { declarationName :: Identifier
  , declarationValue :: Expression
  , declarationSpan :: Maybe Span
  } deriving (Eq, Show, Read)

data FunctionDeclaration = FunctionDeclaration
  { functionName :: Identifier
  , functionBoundParams :: [Identifier]
  , functionSignature :: FunctionSignature
  , functionBody :: Expression
  , functionSpan :: Maybe Span
  } deriving (Eq, Show, Read)

data ForeignImport = ForeignImport
  { foreignTarget :: ForeignTarget
  , foreignName :: Identifier
  , foreignSymbol :: String
  , foreignSignature :: ForeignSignature
  , foreignSpan :: Maybe Span
  } deriving (Eq, Show, Read)

topLevelName :: TopLevel -> String
topLevelName item = case item of
  TopDeclaration d -> identifierName (declarationName d)
  TopFunction f -> identifierName (functionName f)
  TopForeign f -> identifierName (foreignName f)