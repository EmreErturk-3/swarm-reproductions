/*
 * Environment of Bodi et al. (2009) for a Kilobot swarm in ARGoS.
 *
 * PreStep():  virtual sensors, as the overhead controller of a physical
 *             Kilobot set-up (ARK) would provide them:
 *               - illuminance under each robot, read with get_ambientlight();
 *               - wall contact, sent as an overhead-controller message.
 * PostStep(): once per simulated second, logs how many robots are waiting,
 *             inside the target zone, and both.
 * GetFloorColor(): draws the illuminance field on the arena floor.
 */
#ifndef BEECLUST_LOOP_FUNCTIONS_H
#define BEECLUST_LOOP_FUNCTIONS_H

#include <argos3/core/simulator/loop_functions.h>
#include <argos3/plugins/robots/kilobot/simulator/kilobot_entity.h>
#include <argos3/plugins/robots/kilobot/simulator/kilobot_communication_medium.h>
#include <argos3/plugins/simulator/entities/box_entity.h>

#include <fstream>
#include <string>
#include <vector>

class CCI_KilobotController;

using namespace argos;

class CBeeclustLoopFunctions : public CLoopFunctions {

public:

   void Init(TConfigurationNode& t_tree) override;
   void Reset() override;
   void Destroy() override;
   void PreStep() override;
   void PostStep() override;
   CColor GetFloorColor(const CVector2& c_position) override;

   /** Illuminance [lux] at a point of the arena floor (Bodi et al. 2009, Fig. 4). */
   Real Illuminance(const CVector2& c_position) const;

private:

   struct SRobot {
      CKilobotEntity* Entity;
      CCI_KilobotController* Controller;
   };

   void CollectEntities();
   bool IsFacingWall(CKilobotEntity& c_robot) const;
   /** Centre of the robot's body. */
   static CVector2 Position(CKilobotEntity& c_robot);
   static CVector2 Heading(CKilobotEntity& c_robot);

   /* Light field, scaled by the patch size [m] of the paper's arena. */
   CVector2 m_cLightSpot;
   CVector2 m_cShadowSpot;
   Real m_fDecayLength = 0.0;

   std::vector<SRobot> m_vecRobots;
   std::vector<CBoxEntity*> m_vecWalls;
   CKilobotCommunicationMedium* m_pcMedium = nullptr;
   message_t m_tWallMessage;
   UInt32 m_unTicksPerSecond = 0;
   std::string m_strOutputPath;
   std::ofstream m_cOutput;
};

#endif
