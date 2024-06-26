# Reinforcement Learning-driven Data-intensive Workflow Scheduling for Volunteer Edge-Cloud


| ![System](/Figures/system.png) | ![Model](/Figures/model.jpg) |
|---------------------------------|-------------------------------|


In recent times, Volunteer Edge-Cloud (VEC) has gained traction as a cost-effective, community computing paradigm to support data-intensive scientific workflows. However, due to the highly distributed and heterogeneous nature of VEC resources, centralized workflow task scheduling remains a challenge. In this paper, we propose a Reinforcement Learning (RL)-driven data-intensive scientific workflow scheduling approach that takes into consideration: i) workflow requirements, ii) VEC resources’ preference on workflows, and iii) diverse VEC resource policies, to ensure robust resource allocation. We formulate the long-term average performance optimization problem as a Markov Decision Process, which is solved using an event-based Asynchronous Advantage Actor-Critic based RL approach. Our extensive simulations and testbed implementations demonstrate our approach’s benefits over popular baseline strategies in terms of workflow requirement satisfaction, VEC preference satisfaction, and available VEC resource utilization.

