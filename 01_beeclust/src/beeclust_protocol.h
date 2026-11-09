/*
 * Constants shared by the Kilobot controller (beeclust.c) and the ARGoS loop
 * functions (beeclust_loop_functions.cpp). Plain C, so both sides can include it.
 */
#ifndef BEECLUST_PROTOCOL_H
#define BEECLUST_PROTOCOL_H

/*
 * Message types (user range 0-127 of the Kilobot message format).
 *  - ROBOT: beacon broadcast by every robot; its received distance is used to
 *    detect robot-to-robot contact.
 *  - WALL:  virtual wall-contact sensor, sent by the overhead controller (the
 *    loop functions in simulation, ARK on physical Kilobots).
 */
#define BEECLUST_MSG_ROBOT 1
#define BEECLUST_MSG_WALL  2

/*
 * LED colour in the 2-bit-per-channel encoding of kilolib's RGB(r, g, b) macro.
 * The colours follow Bodi et al. (2009), Fig. 2: blue = waiting, red = driving.
 * The loop functions classify a robot as waiting by its LED colour, as an
 * overhead camera would.
 */
#define BEECLUST_COLOR(r, g, b) (((r) & 3) | (((g) & 3) << 2) | (((b) & 3) << 4))
#define BEECLUST_COLOR_DRIVING  BEECLUST_COLOR(1, 0, 0)
#define BEECLUST_COLOR_WAITING  BEECLUST_COLOR(0, 0, 1)

#endif /* BEECLUST_PROTOCOL_H */
