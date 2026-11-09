/*
 * BEECLUST aggregation on the Kilobot.
 *
 * Implements the "light finder" controller of
 *   M. Bodi, R. Thenius, T. Schmickl, K. Crailsheim (2009). Robustness of two
 *   interacting robot swarms using the BEECLUST algorithm. Proc. MATHMOD 2009,
 *   pp. 904-912.
 * BEECLUST itself is due to Schmickl et al. (2009), Autonomous Agents and
 * Multi-Agent Systems 18(1):133-155.
 *
 * State machine (Bodi et al. 2009, Fig. 1):
 *   MOVE --wall contact-->  TURN --> MOVE
 *   MOVE --robot contact--> WAIT for w(e) --> TURN --> MOVE
 * The waiting time w grows sigmoidally with the local illuminance e (Eqs. 1-2),
 * so robots that meet in bright places stay together longer and clusters form
 * there without any robot sensing a gradient.
 *
 * Kilobot-specific choices are listed in README.md, section "Adaptations".
 */
#include <kilolib.h>
#include <math.h>
#include "beeclust_protocol.h"

#ifndef TICKS_PER_SEC
#define TICKS_PER_SEC 32 /* kilo_ticks per second on hardware */
#endif

#ifndef BEECLUST_TIME_SCALE
#error "Define BEECLUST_TIME_SCALE (Kilobot seconds per paper second); see README.md."
#endif

#define PI 3.14159265358979

/* Waiting-time model: Bodi et al. (2009), Eqs. 1-2 and Table 1. */
#define THETA        0.18  /* sensor value per lux                         */
#define E_SENSOR_MAX 180.0 /* e_max, saturation of the sensor value        */
#define W_MAX        60.0  /* w_max, maximum waiting time [paper seconds]  */
#define OFFSET       147.0 /* o, sensor value at half the maximum waiting  */
#define STEEPNESS    0.5   /* sigma                                        */

/* Kilobot parameters. */
#define LUX_PER_COUNT       1.0   /* calibration of the virtual light sensor  */
/*
 * Message distance that counts as contact. The ARGoS model measures it between
 * the robots' leg axes, 9.2 mm behind the body centres, so touching robots
 * (33 mm between centres) measure 15 to 51 mm depending on their headings.
 * Configurable for the sensitivity analysis (README.md).
 */
#ifndef CONTACT_DISTANCE_MM
#define CONTACT_DISTANCE_MM 52
#endif
#define ESCAPE_DISTANCE_MM  33.0  /* distance driven before contacts count    */
#define FORWARD_SPEED_MM_S  11.3  /* ARGoS model, kilo_straight_* = 48        */
#define TURN_RATE_RAD_S     0.725 /* ARGoS model, one leg at kilo_turn_* = 77 */

typedef enum { MOVE, TURN, WAIT } state_t;

static state_t   state;
static uint32_t  state_end_tick;         /* end of the current TURN or WAIT */
static uint32_t  contacts_ignored_until; /* see ESCAPE_DISTANCE_MM          */
static uint8_t   robot_contact;          /* set by message_rx() each cycle  */
static uint8_t   wall_contact;
static message_t beacon;

static uint32_t seconds_to_ticks(double seconds) {
    return (uint32_t)(seconds * TICKS_PER_SEC + 0.5);
}

/* Uniform random number in [0, 1) built from two hardware random bytes. */
static double uniform01(void) {
    uint16_t r = ((uint16_t)rand_hard() << 8) | rand_hard();
    return r / 65536.0;
}

/* Eq. 1: sensor value e, linear in the illuminance and saturating at e_max. */
static double sensor_value(void) {
    double e = THETA * get_ambientlight() * LUX_PER_COUNT;
    return e < E_SENSOR_MAX ? e : E_SENSOR_MAX;
}

/*
 * Eq. 2: waiting time of a light finder, in paper seconds. The paper prints the
 * exponent as -(e + o)sigma, which would make w constant at w_max; Fig. 3 (onset
 * near 800 lux, i.e. e close to o) shows that -(e - o)sigma is meant.
 */
static double waiting_time(double e) {
    return W_MAX / (1.0 + exp(-(e - OFFSET) * STEEPNESS));
}

static void start_move(void) {
    state = MOVE;
    set_color(BEECLUST_COLOR_DRIVING);
    spinup_motors();
    set_motors(kilo_straight_left, kilo_straight_right);
}

/* Turn on the spot by an angle drawn uniformly from (-pi, pi). */
static void start_turn(void) {
    double angle = (2.0 * uniform01() - 1.0) * PI;
    state = TURN;
    set_color(BEECLUST_COLOR_DRIVING);
    spinup_motors();
    if (angle > 0.0)
        set_motors(0, kilo_turn_right); /* counter-clockwise */
    else
        set_motors(kilo_turn_left, 0);  /* clockwise         */
    state_end_tick = kilo_ticks + seconds_to_ticks(fabs(angle) / TURN_RATE_RAD_S);
}

static void start_wait(void) {
    double w = waiting_time(sensor_value()) * BEECLUST_TIME_SCALE;
    state = WAIT;
    set_color(BEECLUST_COLOR_WAITING);
    set_motors(0, 0);
    state_end_tick = kilo_ticks + seconds_to_ticks(w);
}

static void message_rx(message_t *msg, distance_measurement_t *d) {
    if (msg->type == BEECLUST_MSG_WALL)
        wall_contact = 1;
    else if (msg->type == BEECLUST_MSG_ROBOT && estimate_distance(d) <= CONTACT_DISTANCE_MM)
        robot_contact = 1;
}

static message_t *message_tx(void) {
    return &beacon;
}

static void setup(void) {
    beacon.type = BEECLUST_MSG_ROBOT;
    beacon.crc = message_crc(&beacon);
    start_move();
}

static void loop(void) {
    switch (state) {
    case MOVE:
        if (wall_contact)
            start_turn();
        else if (robot_contact && kilo_ticks >= contacts_ignored_until)
            start_wait();
        break;
    case WAIT:
        if (kilo_ticks >= state_end_tick) {
            start_turn();
            /* state_end_tick now marks the end of the turn. */
            contacts_ignored_until =
                state_end_tick + seconds_to_ticks(ESCAPE_DISTANCE_MM / FORWARD_SPEED_MM_S);
        }
        break;
    case TURN:
        if (kilo_ticks >= state_end_tick)
            start_move();
        break;
    }
    /* Contacts are re-sensed from the messages of the next cycle. */
    robot_contact = 0;
    wall_contact = 0;
}

int main(void) {
    kilo_init();
    kilo_message_rx = message_rx;
    kilo_message_tx = message_tx;
    kilo_start(setup, loop);
    return 0;
}
