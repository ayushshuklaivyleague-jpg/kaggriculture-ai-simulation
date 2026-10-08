import kaggle_environments
import main
import main_backup

def main_test():
    for k in [10, 12, 14]:
        print(f"\n=================== Testing _OR2_SN_K = {k} ===================")
        main._OR2_SN_K = k
        results = []
        for seed in [29453000, 29453001, 29453002, 29453003, 29453004]:
            for seat in [0, 1]:
                env = kaggle_environments.make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
                if seat == 0:
                    env.run([main.agent, main_backup.agent])
                    r_new, r_old = env.steps[-1][0].reward, env.steps[-1][1].reward
                else:
                    env.run([main_backup.agent, main.agent])
                    r_new, r_old = env.steps[-1][1].reward, env.steps[-1][0].reward
                m = r_new - r_old
                results.append((seed, seat, r_new, r_old, m))
                print(f"Seed {seed} Seat {seat}: New=${r_new:.0f} vs Old=${r_old:.0f} | Margin={m:+.0f}")
        wins = sum(1 for _,_,_,_,m in results if m > 5)
        losses = sum(1 for _,_,_,_,m in results if m < -5)
        ties = sum(1 for _,_,_,_,m in results if abs(m) <= 5)
        mean_m = sum(m for _,_,_,_,m in results) / len(results)
        print(f"Summary for k={k}: {wins}W - {losses}L - {ties}T | Mean Margin: {mean_m:+.0f}")

if __name__ == "__main__":
    main_test()
