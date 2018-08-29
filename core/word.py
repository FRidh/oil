"""
word.py -- Functions for using words as "tokens".
"""

from osh.meta import Id, Kind, LookupKind
from core import util
from osh.meta import ast
from asdl import const

p_die = util.p_die

word_e = ast.word_e
word_part_e = ast.word_part_e
assign_op_e = ast.assign_op_e


def _LiteralPartId(p):
  """
  If the WordPart consists of a single literal token, return its Id.  Used for
  Id.KW_For, or Id.RBrace, etc.
  """
  if p.tag == word_part_e.LiteralPart:
    return p.token.id
  else:
    return Id.Undefined_Tok  # unequal to any other Id


def _EvalWordPart(part):
  """Evaluate a WordPart at PARSE TIME.

  Used for:

  1. here doc delimiters
  2. function names
  3. for loop variable names
  4. Compiling constant regex words at parse time
  5. a special case for ${a////c} to see if we got a leading slash in the
  pattern.

  Returns:
    3-tuple of
      ok: bool, success.  If there are parts that can't be statically
        evaluated, then we return false.
      value: a string (not Value)
      quoted: whether any part of the word was quoted
  """
  if part.tag == word_part_e.ArrayLiteralPart:
    # Array literals aren't good for any of our use cases.  TODO: Rename
    # EvalWordToString?
    return False, '', False

  elif part.tag == word_part_e.LiteralPart:
    return True, part.token.val, False

  elif part.tag == word_part_e.EscapedLiteralPart:
    val = part.token.val
    assert len(val) == 2, val  # e.g. \*
    assert val[0] == '\\'
    s = val[1]
    return True, s, True

  elif part.tag == word_part_e.SingleQuotedPart:
    s = ''.join(t.val for t in part.tokens)
    return True, s, True

  elif part.tag == word_part_e.DoubleQuotedPart:
    ret = ''
    for p in part.parts:
      ok, s, _ = _EvalWordPart(p)
      if not ok:
        return False, '', True
      ret += s

    return True, ret, True  # At least one part was quoted!

  elif part.tag in (
      word_part_e.CommandSubPart, word_part_e.SimpleVarSub,
      word_part_e.BracedVarSub, word_part_e.TildeSubPart,
      word_part_e.ArithSubPart):
    return False, '', False

  else:
    raise AssertionError(part.tag)


def StaticEval(w):
  """Evaluate a CompoundWord at PARSE TIME.
  """
  ret = ''
  quoted = False

  # e.g. for ( instead of for (( is a token word
  if w.tag != word_e.CompoundWord:
    return False, ret, quoted

  for part in w.parts:
    ok, s, q = _EvalWordPart(part)
    if not ok:
      return False, '', quoted
    if q:
      quoted = True  # at least one part was quoted
    ret += s
  return True, ret, quoted


def LeftMostSpanForPart(part):
  # TODO: Write unit tests in ui.py for error values

  if part.tag == word_part_e.ArrayLiteralPart:
    if not part.words:
      return const.NO_INTEGER
    else:
      return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

  elif part.tag == word_part_e.LiteralPart:
    # Just use the token
    return part.token.span_id

  elif part.tag == word_part_e.EscapedLiteralPart:
    return part.token.span_id

  elif part.tag == word_part_e.SingleQuotedPart:
    if part.tokens:
      return part.tokens[0].span_id
    else:
      return const.NO_INTEGER

  elif part.tag == word_part_e.DoubleQuotedPart:
    if part.parts:
      return LeftMostSpanForPart(part.parts[0])
    else:
      # We need the double quote location
      return const.NO_INTEGER

  elif part.tag == word_part_e.SimpleVarSub:
    return part.token.span_id

  elif part.tag == word_part_e.BracedVarSub:
    return part.spids[0]

  elif part.tag == word_part_e.CommandSubPart:
    return part.spids[0]

  elif part.tag == word_part_e.TildeSubPart:
    return const.NO_INTEGER

  elif part.tag == word_part_e.ArithSubPart:
    # begin, end
    return part.spids[0]

  elif part.tag == word_part_e.ExtGlobPart:
    # This is the smae as part.op.span_id, but we want to be consistent with
    # left/right.  Not sure I want to add a right token just for the spid.
    return part.spids[0]
    #return part.op.span_id  # e.g. @( is the left-most token

  elif part.tag == word_part_e.BracedAltPart:
    return const.NO_INTEGER

  elif part.tag == word_part_e.EmptyPart:
    return const.NO_INTEGER

  else:
    raise AssertionError(part.__class__.__name__)


def _RightMostSpanForPart(part):
  # TODO: Write unit tests in ui.py for error values

  if part.tag == word_part_e.ArrayLiteralPart:
    # TODO: Return )
    return LeftMostSpanForWord(part.words[0])  # Hm this is a=(1 2 3)

  elif part.tag == word_part_e.LiteralPart:
    # Just use the token
    return part.token.span_id

  elif part.tag == word_part_e.EscapedLiteralPart:
    return part.token.span_id

  elif part.tag == word_part_e.SingleQuotedPart:
    return part.spids[1]  # right '

  elif part.tag == word_part_e.DoubleQuotedPart:
    return part.spids[1]  # right "

  elif part.tag == word_part_e.SimpleVarSub:
    return part.token.span_id

  elif part.tag == word_part_e.BracedVarSub:
    spid = part.spids[0]
    assert spid != const.NO_INTEGER
    return spid

  elif part.tag == word_part_e.CommandSubPart:
    return part.spids[1]

  elif part.tag == word_part_e.TildeSubPart:
    return const.NO_INTEGER

  elif part.tag == word_part_e.ArithSubPart:
    return const.NO_INTEGER

  elif part.tag == word_part_e.ExtGlobPart:
    return part.spids[1]

  else:
    raise AssertionError(part.tag)


def LeftMostSpanForWord(w):
  # For now it returns a LineSpan.  That's all you know how to print.
  #
  # Runtime errors may be different.
  #
  # TokenWord: just use token.line_span
  # LiteralPart: token.line_span
  # composites: just use the first part for now, but show the stack trace:
  #   $(( 1 +  + ))
  #   ^~~
  #   In arithmetic substitution
  #   $(( 1 +  + ))
  #            ^
  #            Invalid argument to + operator

  # TODO: Really we should use par
  if w.tag == word_e.CompoundWord:
    if len(w.parts) == 0:
      return const.NO_INTEGER
    else:
      begin = w.parts[0]
      # TODO: We need to combine LineSpan()?  If they're both on the same line,
      # return them both.  If they're not, then just use "begin"?
      return LeftMostSpanForPart(begin)

  elif w.tag == word_e.TokenWord:
    return w.token.span_id

  elif w.tag == word_e.BracedWordTree:
    if len(w.parts) == 0:
      return const.NO_INTEGER
    else:
      begin = w.parts[0]
      # TODO: We need to combine LineSpan()?  If they're both on the same line,
      # return them both.  If they're not, then just use "begin"?
      return LeftMostSpanForPart(begin)

  elif w.tag == word_e.StringWord:
    # There is no place to store this now?
    return const.NO_INTEGER


def RightMostSpanForWord(w):
  """Needed for here doc delimiters."""
  if w.tag == word_e.CompoundWord:
    if len(w.parts) == 0:
      # TODO: Use EmptyWord instead
      raise AssertionError("CompoundWord shouldn't be empty")
    else:
      end = w.parts[-1]
      return _RightMostSpanForPart(end)

  # It's a TokenWord?
  return w.token.span_id


# From bash, general.c, unquoted_tilde_word():
# POSIX.2, 3.6.1:  A tilde-prefix consists of an unquoted tilde character at
# the beginning of the word, followed by all of the characters preceding the
# first unquoted slash in the word, or all the characters in the word if there
# is no slash...If none of the characters in the tilde-prefix are quoted, the
# characters in the tilde-prefix following the tilde shell be treated as a
# possible login name. 
#define TILDE_END(c)    ((c) == '\0' || (c) == '/' || (c) == ':')
#
# So an unquoted tilde can ALWAYS start a new lex mode?  You respect quotes and
# substitutions.
#
# We only detect ~Lit_Chars and split.  So we might as well just write a regex.

def TildeDetect(word):
  """Detect tilde expansion in a word.

  It might begin with  LiteralPart that needs to be turned into a TildeSubPart.
  (It depends on whether the second token begins with slash).

  If so, it return a new word.  Otherwise return None.

  NOTE:
  - The regex for Lit_TildeLike could be expanded.  Right now it's
    conservative, like Lit_Chars without the /.
  - It's possible to write this in a mutating style, since only the first token
    is changed.  But note that we CANNOT know this during lexing.
  """
  # NOTE: BracedWordTree, EmptyWord, etc. can't be tilde expanded
  if word.tag != word_e.CompoundWord:
    return None

  assert word.parts, word

  part0 = word.parts[0]
  if _LiteralPartId(part0) != Id.Lit_TildeLike:
    return None

  if len(word.parts) == 1:  # can't be zero
    tilde_part = ast.TildeSubPart(part0.token)
    return ast.CompoundWord([tilde_part])

  part1 = word.parts[1]
  # NOTE: We could inspect the raw tokens.
  if _LiteralPartId(part1) == Id.Lit_Chars and part1.token.val.startswith('/'):
    tilde_part = ast.TildeSubPart(part0.token)
    return ast.CompoundWord([tilde_part] + word.parts[1:])

  # It could be something like '~foo:bar', which doesn't have a slash.
  return None


def TildeDetectAll(words):
  out = []
  for w in words:
    t = TildeDetect(w)
    if t:
      out.append(t)
    else:
      out.append(w)
  return out


def HasArrayPart(w):
  """Used in cmd_parse."""
  assert w.tag == word_e.CompoundWord

  for part in w.parts:
    if part.tag == word_part_e.ArrayLiteralPart:
      return True
  return False


def AsFuncName(w):
  assert w.tag == word_e.CompoundWord

  ok, s, quoted = StaticEval(w)
  if not ok:
    return False, ''
  if quoted:
    # Function names should not have quotes
    if len(w.parts) != 1:
      return False, ''
  return True, s


def AsArithVarName(w):
  """Returns a string if this word looks like an arith var; otherwise False.

  NOTE: This can't be combined with LooksLikeAssignment because VarLike and
  ArithVarLike must be different tokens.  Otherwise _ReadCompoundWord will be
  confused between array assigments foo=(1 2) and function calls foo(1, 2).
  """
  assert w.tag == word_e.CompoundWord

  if len(w.parts) != 1:
    return ""

  part0 = w.parts[0]
  if _LiteralPartId(part0) != Id.Lit_ArithVarLike:
    return False

  return part0.token.val


def LooksLikeAssignment(w):
  """Tests whether a word looks like FOO=bar.

  Returns:
    (string, op, CompoundWord) if it looks like FOO=bar
    False                      if it doesn't

  s=1
  s+=1
  s[x]=1
  s[x]+=1

  a=()
  a+=()
  a[x]=()
  a[x]+=()  # Not valid because arrays can't be nested.

  NOTE: a[ and s[ might be parsed separately?
  """
  assert w.tag == word_e.CompoundWord
  if len(w.parts) == 0:
    return False

  part0 = w.parts[0]
  if _LiteralPartId(part0) != Id.Lit_VarLike:
    return False

  s = part0.token.val
  assert s.endswith('=')
  if s[-2] == '+':
    op = assign_op_e.PlusEqual
    name = s[:-2]
  else:
    op = assign_op_e.Equal
    name = s[:-1]

  rhs = ast.CompoundWord()
  if len(w.parts) == 1:
    # This is necessary so that EmptyUnquoted elision isn't applied.  EMPTY= is
    # like EMPTY=''.
    # TODO: Change to EmptyWord
    rhs.parts.append(ast.EmptyPart())
  else:
    for p in w.parts[1:]:
      rhs.parts.append(p)

  return name, op, rhs


# TODO:
# - local/declare should use this.
# - Doesn't work with 'readonly' or 'export'
# - global is parsed at the top level with LhsIndexedLike.
def LooksLikeLhsIndex(s):
  """Tests if a STRING looks like a[x + 1]=b

  # After EvalStatic, do another around of lexing at runtime.
  # Use osh/lex.py.

  Returns:
    (string, arith_expr) if it looks like a[x + 1]=b
    LhsIndexedName?

    False                  if it doesn't
  """
  # PROBLEM: What arena tokens to use?


def KeywordToken(w):
  """Tests if a word is an assignment or control flow word.

  Returns:
    kind, token
  """
  assert w.tag == word_e.CompoundWord

  err = (Kind.Undefined, None)
  if len(w.parts) != 1:
    return err

  token_type = _LiteralPartId(w.parts[0])
  if token_type == Id.Undefined_Tok:
    return err

  token_kind = LookupKind(token_type)
  if token_kind in (Kind.Assign, Kind.ControlFlow):
    return token_kind, w.parts[0].token

  return err


#
# Polymorphic between TokenWord and CompoundWord
#

def ArithId(node):
  if node.tag == word_e.TokenWord:
    return node.token.id

  assert node.tag == word_e.CompoundWord
  return Id.Word_Compound


def BoolId(node):
  if node.tag == word_e.StringWord:  # for test/[
    return node.id

  if node.tag == word_e.TokenWord:
    return node.token.id

  # Assume it's a CompoundWord
  #assert node.tag == word_e.CompoundWord

  if len(node.parts) != 1:
    return Id.Word_Compound

  token_type = _LiteralPartId(node.parts[0])
  if token_type == Id.Undefined_Tok:
    return Id.Word_Compound  # It's a regular word

  # This is outside the BoolUnary/BoolBinary namespace, but works the same.
  if token_type in (Id.KW_Bang, Id.Lit_DRightBracket):
    return token_type  # special boolean "tokens"

  token_kind = LookupKind(token_type)
  if token_kind in (Kind.BoolUnary, Kind.BoolBinary):
    return token_type  # boolean operators

  return Id.Word_Compound


def CommandId(node):
  if node.tag == word_e.TokenWord:
    return node.token.id

  # Assume it's a CompoundWord
  assert node.tag == word_e.CompoundWord

  # Has to be a single literal part
  if len(node.parts) != 1:
    return Id.Word_Compound

  token_type = _LiteralPartId(node.parts[0])
  if token_type == Id.Undefined_Tok:
    return Id.Word_Compound

  elif token_type in (Id.Lit_LBrace, Id.Lit_RBrace):
    return token_type

  token_kind = LookupKind(token_type)
  if token_kind == Kind.KW:
    return token_type

  return Id.Word_Compound


def CommandKind(w):
  if w.tag == word_e.TokenWord:
    return LookupKind(w.token.id)

  # NOTE: This is a bit inconsistent with CommandId, because we never retur
  # Kind.KW (or Kind.Lit).  But the CommandParser is easier to write this way.
  return Kind.Word


# Stubs for converting RHS of assignment to expression mode.
def IsVarSub(w):
  # Return whether it's any var sub, or a double quoted one
  return False
