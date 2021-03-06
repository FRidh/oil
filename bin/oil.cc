#include "types_asdl.h"
#include "syntax_asdl.h"
#include "runtime_asdl.h"

// From _devbuild/gen.  TODO: rename these?
#include "osh-types.h"
#include "id.h"
#include "osh-lex.h"


#include "mylib.h"

// TODO: Should this just call oil::main(argv) or something?

int main(int argc, char **argv) {
  log("sizeof(int): %d", sizeof(int));

  Str* s = new Str("foo");
  int id;
  int end_pos;
  // TODO: mylib::Str should use unsigned char internally?
  MatchOshToken(
      lex_mode__ShCommand, (const unsigned char*)s->data_, s->len_, 0,
      &id, &end_pos);

  log("id = %d", id);
  log("end_pos = %d", end_pos);
}
