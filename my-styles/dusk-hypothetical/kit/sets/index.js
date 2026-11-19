// The kit's sets by name (catalog.json "sets"); every set exports build() → {group, lights, anchors}.
import * as classroom from './classroom.js';
import * as lockers from './lockers.js';
import * as gym from './gym.js';
import * as street from './street.js';
import * as bedroom from './bedroom.js';
import * as cafeteria from './cafeteria.js';
import * as stadium from './stadium.js';
import * as voidSet from './void.js';
import * as court from './court.js';
import * as rooftop from './rooftop.js';
import * as parking from './parking.js';
import * as streetDusk from './street-dusk.js';

export const SETS = { classroom, lockers, gym, street, bedroom, cafeteria, stadium, void: voidSet, court, rooftop, parking, 'street-dusk': streetDusk };
