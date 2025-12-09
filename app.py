from core import UIRoot, UIFont, UIVisuals
from widgets import UIWindow


# ─── Bootstrapper ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    
    # engine
    rt = UIRoot(1000, 600, 60)
    
        
    # font provider
    ft = UIFont()
    rt.add(ft)
    
    # visuals provider
    vis = UIVisuals()
    rt.add(vis)
    
    # load assets
    ft.initialize('JetBrainsMono-Bold.ttf', 15)
    vis.initialize()
    
    
    win1 = UIWindow(50, 50, 250, 200, 'UIWindow')
    rt.add(win1)
    
    win2 = UIWindow(10, 10, 150, 100, 'UIWindow')
    win1.add(win2)
    
    win3 = UIWindow(100, 100, 150, 100, 'UIWindow')
    rt.add(win3)
    
    # commit 
    
    rt.run()
    
       
    
    
    

