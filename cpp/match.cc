// match.cc

#include "match.h"

// C includes
#include "id.h"
#include "osh-types.h"
#include "osh-lex.h"

namespace match {

Tuple2<Id_t, int>* OneToken(lex_mode_t lex_mode, Str* line, int start_pos) {
  int id;
  int end_pos;
  // TODO: get rid of these casts
  MatchOshToken(static_cast<int>(lex_mode),
                reinterpret_cast<const unsigned char*>(line->data_),
                line->len_, start_pos, &id, &end_pos);
  return new Tuple2<Id_t, int>(static_cast<Id_t>(id), end_pos);
}

}
