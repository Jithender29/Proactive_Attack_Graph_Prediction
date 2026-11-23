##### **Initial Problem Statement:** 

A predictive security engine that can be accessed through an API. When integrated with a website, application, server, or security system, it receives security events/logs, reconstructs the ongoing attack sequence, and predicts the attacker's most probable next action or target.



#### **Important thing to consider**



* ##### Different websites, applications, and servers have different architectures, assets, services, network topologies, and possible attack paths. Therefore, a prediction based only on previously observed attack sequences may produce an attack that is statistically likely but technically impossible in the current environment.

###### &#x09;**Example:**

&#x09;	The model predicts lateral movement, but the target environment contains only one isolated server. In that case, lateral movement may not be feasible.

###### &#x09;**Probable Solution**	

&#x09;	Make the prediction engine environment-aware. Along with security events/logs, the engine should maintain a representation of the target environment—including its assets, 		network topology, services, operating systems, users, and relationships between systems.



* ##### The engine should not directly consume every piece of data from the website/application. For the first version, we need a      simple, standardized representation of the attack activity observed so far. Different security tools produce different logs, so raw logs should first be converted into a common format.

###### &#x09; **Probable Solution**

&#x09;	1. Attack sequence — the security-relevant actions observed so far, preferably mapped to MITRE ATT\&CK techniques.

&#x09;	2. Basic environment information — only enough information to determine whether a predicted action is possible, such as available hosts and their basic relationships.



* ##### The engine should not simply output "an attack will happen." It should provide a specific, understandable prediction that can be evaluated against what actually happens next.

###### &#x09;   **Probable Solution**

&#x09;	**1.** Predicted next attack technique

&#x09;	2. Probability/confidence

&#x09;	3. Predicted target — if applicable



* ##### The AI doesn't "understand" an attack sequence automatically. It needs historical examples where the \*\*order of attack techniques is known\*\* so it can learn which techniques commonly follow others.

###### &#x09;   **Probable Solution**

&#x09;	Give the AI many historical attack sequences and train it to predict the next technique from the techniques that have already occurred.

